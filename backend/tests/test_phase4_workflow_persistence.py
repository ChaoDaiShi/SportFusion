"""
Phase 4 regression tests — batch persistence, review workflow, formal/demo/test isolation.
"""

import unittest

from services.batch_service import (
    BatchStatus,
    BatchStore,
    DataMode,
    get_batch_store,
)
from services.review_workflow_service import (
    ReviewTask,
    arbitrate,
    create_review_tasks,
    determine_priority,
    get_review_stats,
    load_priority_rules,
    submit_review,
)


class TestBatchPersistence(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.TemporaryDirectory()
        self.store = BatchStore(storage_dir=self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_create_batch(self):
        batch = self.store.create_batch(
            data_mode=DataMode.TEST.value,
            source_file_name="test.csv",
            total_rows=100,
            operator="test-runner",
        )
        self.assertTrue(batch.batch_id.startswith("BATCH-"))
        self.assertEqual(batch.data_mode, "test")
        self.assertEqual(batch.status, BatchStatus.CREATED.value)

    def test_batch_persists_across_store_instances(self):
        batch = self.store.create_batch(data_mode=DataMode.TEST.value, total_rows=10)
        store2 = BatchStore(storage_dir=self.tmpdir.name)
        loaded = store2.get_batch(batch.batch_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.batch_id, batch.batch_id)

    def test_update_status_and_lock(self):
        batch = self.store.create_batch(data_mode=DataMode.TEST.value)
        self.store.update_status(batch.batch_id, BatchStatus.RECOGNITION_DONE.value)
        loaded = self.store.get_batch(batch.batch_id)
        self.assertEqual(loaded.status, BatchStatus.RECOGNITION_DONE.value)

    def test_lock_batch(self):
        batch = self.store.create_batch(data_mode=DataMode.TEST.value)
        self.store.lock_batch(batch.batch_id, "operator")
        self.assertTrue(self.store.is_locked(batch.batch_id))

    def test_locked_batch_cannot_save_results(self):
        batch = self.store.create_batch(data_mode=DataMode.TEST.value)
        self.store.lock_batch(batch.batch_id)
        with self.assertRaises(ValueError):
            self.store.save_results(batch.batch_id, "recognition", [{"test": 1}])

    def test_audit_log_entries(self):
        batch = self.store.create_batch(data_mode=DataMode.TEST.value)
        entries = self.store.get_audit_log(batch.batch_id)
        self.assertGreaterEqual(len(entries), 1)
        self.assertEqual(entries[0].action, "CREATE_BATCH")

    def test_list_batches_filters_by_mode(self):
        self.store.create_batch(data_mode=DataMode.FORMAL.value)
        self.store.create_batch(data_mode=DataMode.DEMO.value)
        formal = self.store.list_batches(data_mode=DataMode.FORMAL.value)
        demo = self.store.list_batches(data_mode=DataMode.DEMO.value)
        self.assertGreaterEqual(len(formal), 1)
        self.assertGreaterEqual(len(demo), 1)

    def test_batch_has_version_metadata(self):
        batch = self.store.create_batch(data_mode=DataMode.TEST.value)
        self.assertTrue(batch.dictionary_version)
        self.assertTrue(batch.feature_schema_version)

    def test_get_batch_not_found(self):
        self.assertIsNone(self.store.get_batch("NONEXISTENT"))

    def test_save_and_load_results(self):
        batch = self.store.create_batch(data_mode=DataMode.TEST.value)
        rec_results = [{"enterprise_id": "1", "sport_score": 0.5}]
        self.store.save_results(batch.batch_id, "recognition", rec_results)
        loaded = self.store.load_results(batch.batch_id, "recognition")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["sport_score"], 0.5)


class TestReviewWorkflow(unittest.TestCase):
    def test_priority_rules_load(self):
        rules = load_priority_rules()
        self.assertIn("priorities", rules)
        for p in ["P1", "P2", "P3", "P4"]:
            self.assertIn(p, rules["priorities"])

    def test_direct_code_text_conflict_is_p1(self):
        rec = {"is_sport": True, "sport_score": 0.05, "code_type": "direct",
               "confidence": 0.5, "evidence_relation": "direct_code_text_conflict",
               "is_crossover": False, "keywords": [], "total_business_lines": 2, "sport_business_lines": 0}
        priority, _triggers, _ = determine_priority(rec)
        self.assertEqual(priority, "P1")

    def test_standard_candidate_is_p3(self):
        rec = {"is_sport": True, "sport_score": 0.40, "code_type": "direct",
               "confidence": 0.85, "evidence_relation": "direct_code_text_support",
               "is_crossover": False, "keywords": ["体育赛事", "运营"],
               "total_business_lines": 2, "sport_business_lines": 1}
        priority, _, _ = determine_priority(rec)
        self.assertIn(priority, ["P3", "P2"])

    def test_non_sport_is_p4(self):
        rec = {"is_sport": False, "sport_score": 0.0, "code_type": "none",
               "confidence": 0.0, "evidence_relation": "no_sport_evidence",
               "is_crossover": False, "keywords": [], "total_business_lines": 1, "sport_business_lines": 0}
        priority, _, _ = determine_priority(rec)
        self.assertEqual(priority, "P4")

    def test_create_review_tasks_returns_correct_count(self):
        recs = [
            {"enterprise_id": "1", "is_sport": True, "sport_score": 0.5, "code_type": "direct",
             "confidence": 0.9, "evidence_relation": "direct_code_text_support",
             "is_crossover": False, "keywords": ["体育赛事"], "total_business_lines": 2, "sport_business_lines": 1,
             "enterprise_name": "TestCo", "credit_code": "CC001"},
            {"enterprise_id": "2", "is_sport": False, "sport_score": 0.0, "code_type": "none",
             "confidence": 0.0, "evidence_relation": "no_sport_evidence",
             "is_crossover": False, "keywords": [], "total_business_lines": 1, "sport_business_lines": 0,
             "enterprise_name": "OtherCo", "credit_code": "CC002"},
        ]
        tasks = create_review_tasks(recs, batch_id="BATCH-TEST")
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].priority, "P3")
        self.assertEqual(tasks[1].priority, "P4")

    def test_dual_review_submit_and_consensus(self):
        task = ReviewTask(task_id="T1", batch_id="B1", status="assigned")
        task = submit_review(task, "A", "yes", "体育赛事", 0.5, "evidence strong")
        self.assertEqual(task.status, "in_review")
        task = submit_review(task, "B", "yes", "体育赛事", 0.5, "agree")
        self.assertEqual(task.status, "confirmed")
        self.assertEqual(task.final_sport_attribute, "yes")

    def test_dual_review_disputed(self):
        task = ReviewTask(task_id="T1", batch_id="B1", status="assigned")
        task = submit_review(task, "A", "yes", "体育赛事", 0.5)
        task = submit_review(task, "B", "no", "", 0.0)
        self.assertEqual(task.status, "disputed")

    def test_arbitration_resolves_dispute(self):
        task = ReviewTask(task_id="T1", batch_id="B1", status="assigned")
        task = submit_review(task, "A", "yes", "体育赛事", 0.5)
        task = submit_review(task, "B", "no", "", 0.0)
        self.assertEqual(task.status, "disputed")
        task = arbitrate(task, "Arbiter1", "yes", "体育赛事", 0.45, "closer to A")
        self.assertEqual(task.status, "confirmed")
        self.assertEqual(task.final_sport_attribute, "yes")
        self.assertEqual(task.arbiter, "Arbiter1")

    def test_review_stats(self):
        tasks = [
            ReviewTask(task_id="1", priority="P1", status="confirmed"),
            ReviewTask(task_id="2", priority="P2", status="confirmed"),
            ReviewTask(task_id="3", priority="P3", status="disputed"),
            ReviewTask(task_id="4", priority="P4", status="pending"),
        ]
        stats = get_review_stats(tasks)
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["p1_p2_count"], 2)
        self.assertEqual(stats["by_priority"]["P1"], 1)


class TestFormalDemoTestIsolation(unittest.TestCase):
    """Formal must not silently fall back to demo."""

    def test_batch_data_mode_is_immutable_on_create(self):
        store = get_batch_store()
        batch = store.create_batch(data_mode=DataMode.FORMAL.value)
        self.assertEqual(batch.data_mode, DataMode.FORMAL.value)

    def test_demo_batch_distinct_from_formal(self):
        import tempfile
        store = BatchStore(tempfile.mkdtemp())
        f = store.create_batch(data_mode=DataMode.FORMAL.value)
        d = store.create_batch(data_mode=DataMode.DEMO.value)
        self.assertNotEqual(f.batch_id, d.batch_id)
        formals = store.list_batches(data_mode=DataMode.FORMAL.value)
        demos = store.list_batches(data_mode=DataMode.DEMO.value)
        self.assertEqual(len(formals), 1)
        self.assertEqual(len(demos), 1)


if __name__ == "__main__":
    unittest.main()
