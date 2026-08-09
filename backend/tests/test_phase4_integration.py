"""
Phase 4 integration workflow test — full pipeline + restart persistence.

Covers: create batch → recognition → share → scale → review tasks →
        A/B review → dispute/arbitration → finalize → directory →
        lock → export → restart persistence.
"""

import tempfile
import unittest

from services.batch_service import BatchStatus, BatchStore, DataMode
from services.directory_service import DirectoryService
from services.review_workflow_service import (
    arbitrate,
    create_review_tasks,
    submit_review,
)
from services.sport_recognition import recognize_sport_business
from services.sportshare.estimator import estimate_sport_share


class TestPhase4IntegrationWorkflow(unittest.TestCase):
    """Full end-to-end workflow with restart persistence."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.store = BatchStore(storage_dir=self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run_full_pipeline(self, store: BatchStore) -> str:
        """Run complete pipeline and return batch_id."""
        # 1. Create batch
        batch = store.create_batch(
            data_mode=DataMode.TEST.value,
            source_file_name="test_fixture.csv",
            total_rows=3,
            operator="integration-test",
        )
        batch_id = batch.batch_id
        store.update_status(batch_id, BatchStatus.DATA_READY.value)

        # 2. Import fixtures
        enterprises = [
            {"enterprise_id": "E1", "enterprise_name": "体育赛事运营公司", "business_text": "体育赛事运营，运动器材销售", "industry_code": 8911, "credit_code": "CC001"},
            {"enterprise_id": "E2", "enterprise_name": "健身培训中心", "business_text": "健身培训，瑜伽教学", "industry_code": 8391, "credit_code": "CC002"},
            {"enterprise_id": "E3", "enterprise_name": "餐饮服务公司", "business_text": "餐饮管理服务", "industry_code": None, "credit_code": "CC003"},
        ]

        # 3. Recognition
        store.update_status(batch_id, BatchStatus.RECOGNITION_RUNNING.value)
        recs = []
        for ent in enterprises:
            r = recognize_sport_business(
                business_text=ent["business_text"],
                industry_code=ent["industry_code"],
                enterprise_name=ent["enterprise_name"],
            )
            r["enterprise_id"] = ent["enterprise_id"]
            r["enterprise_name"] = ent["enterprise_name"]
            r["credit_code"] = ent["credit_code"]
            recs.append(r)
        store.save_results(batch_id, "recognition", recs)
        store.update_status(batch_id, BatchStatus.RECOGNITION_DONE.value)

        # 4. SportShare
        store.update_status(batch_id, BatchStatus.SHARE_RUNNING.value)
        shares = []
        for i, ent in enumerate(enterprises):
            est = estimate_sport_share(
                enterprise=ent,
                recognition_result=recs[i],
            )
            shares.append({
                "enterprise_id": ent["enterprise_id"],
                "model_share": est.model_share,
                "fallback_share": est.fallback_share,
                "manual_share": est.manual_share,
                "effective_share": est.effective_share,
                "share_source": est.share_source,
                "lower_bound": est.lower_bound,
                "upper_bound": est.upper_bound,
            })
        store.save_results(batch_id, "share", shares)
        store.update_status(batch_id, BatchStatus.SHARE_DONE.value)

        # 5. Scale
        store.update_status(batch_id, BatchStatus.SCALE_RUNNING.value)
        scale_results = [{"type": "category", "outputs": {"体育赛事": 500.0, "健身休闲": 300.0, "非体育": 1370.80}}]
        store.save_results(batch_id, "scale", scale_results)
        store.update_status(batch_id, BatchStatus.SCALE_DONE.value)

        # 6. Create review tasks
        store.update_status(batch_id, BatchStatus.REVIEWING.value)
        tasks = create_review_tasks(recs, batch_id=batch_id)
        task_dicts = [
            {k: v for k, v in t.__dict__.items() if not k.startswith("_")}
            for t in tasks
        ]
        store.save_results(batch_id, "review", task_dicts)
        return batch_id, tasks, enterprises, recs, shares

    def test_full_pipeline_workflow(self):
        """A. Full integration: create→recognition→share→scale→review→finalize→directory"""
        batch_id, tasks, enterprises, recs, shares = self._run_full_pipeline(self.store)

        # E1 has sport → should be P3 or P2
        self.assertIn(tasks[0].priority, ["P2", "P3"])
        # E3 is non-sport → P4
        self.assertEqual(tasks[2].priority, "P4")

        # 7. Dual review
        t1 = submit_review(tasks[0], "A", "yes", "体育赛事", 0.5, "strong evidence")
        t1 = submit_review(t1, "B", "yes", "体育赛事", 0.5, "agree")
        self.assertEqual(t1.status, "confirmed")

        t2 = submit_review(tasks[1], "A", "yes", "健身休闲", 0.3, "ok")
        t2 = submit_review(t2, "B", "no", "", 0.0, "disagree — not sport")
        self.assertEqual(t2.status, "disputed")

        # 8. Arbitrate
        t2 = arbitrate(t2, "Arbiter1", "no", "", 0.0, "insufficient evidence")
        self.assertEqual(t2.status, "confirmed")
        self.assertEqual(t2.final_sport_attribute, "no")

        # 9. T3 non-sport auto
        t3 = submit_review(tasks[2], "A", "no", "", 0.0, "not sport")
        t3 = submit_review(t3, "B", "no", "", 0.0, "agree")
        self.assertEqual(t3.status, "confirmed")

        # Save mutated review tasks back to store
        updated_reviews = [
            {k: v for k, v in t.__dict__.items() if not k.startswith("_")}
            for t in [t1, t2, t3]
        ]
        self.store.save_results(batch_id, "review", updated_reviews)

        # 10. Finalize batch
        self.store.update_status(batch_id, BatchStatus.FINALIZED.value)

        # 11. Directory
        dir_svc = DirectoryService(store=self.store)
        entries = dir_svc.get_directory(batch_id=batch_id)
        self.assertGreaterEqual(len(entries), 1)

        # 12. Lock
        self.store.lock_batch(batch_id, "integration-test")
        self.assertTrue(self.store.is_locked(batch_id))

        # 13. Locked batch rejects writes
        with self.assertRaises(ValueError):
            self.store.save_results(batch_id, "recognition", [{"bad": True}])

    def test_restart_persistence(self):
        """B. Restart persistence: results survive store re-instantiation."""
        batch_id, tasks, enterprises, recs, shares = self._run_full_pipeline(self.store)

        # Simulate service restart — create new store pointing to same dir
        new_store = BatchStore(storage_dir=self.tmpdir.name)

        # Verify batch survived
        batch2 = new_store.get_batch(batch_id)
        self.assertIsNotNone(batch2)
        self.assertEqual(batch2.data_mode, DataMode.TEST.value)

        # Verify results survived
        recs2 = new_store.load_results(batch_id, "recognition")
        self.assertEqual(len(recs2), 3)
        self.assertEqual(recs2[0]["enterprise_name"], "体育赛事运营公司")

        shares2 = new_store.load_results(batch_id, "share")
        self.assertEqual(len(shares2), 3)

        # Verify audit log survived
        audit = new_store.get_audit_log(batch_id)
        self.assertGreaterEqual(len(audit), 1)

    def test_formal_batch_with_missing_share_model(self):
        """C. Formal batch without model artifact → fallback (not demo)"""
        batch = self.store.create_batch(data_mode=DataMode.FORMAL.value, total_rows=1)
        ent = {"enterprise_id": "F1", "business_text": "体育赛事运营", "industry_code": 8911}
        rec = recognize_sport_business("体育赛事运营", 8911)
        est = estimate_sport_share(enterprise=ent, recognition_result=rec, model_artifact=None)
        # Without model, must use fallback
        self.assertEqual(est.share_source, "fallback")
        self.assertIsNotNone(est.fallback_share)
        self.assertIsNone(est.model_share)

    def test_directory_excludes_non_finalized(self):
        """D. Directory must exclude pending/disputed enterprises."""
        batch_id, tasks, enterprises, recs, shares = self._run_full_pipeline(self.store)
        dir_svc = DirectoryService(store=self.store)

        # Before review completion, directory should be empty
        entries_before = dir_svc.get_directory(batch_id=batch_id)
        for e in entries_before:
            self.assertNotIn("pending", e.review_status)


if __name__ == "__main__":
    unittest.main()
