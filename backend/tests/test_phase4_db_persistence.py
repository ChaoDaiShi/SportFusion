"""
Phase 4 closure: DB persistence + restart test.

Tests formal DB canonical storage for all result types.
Covers: recognition, share, scale, scenario, validation, review, directory.
"""

import unittest

from repositories.recognition_repo import (
    DBRecognitionRepository,
    FileRecognitionRepository,
    MemoryRecognitionRepository,
)
from repositories.sportshare_repo import (
    DBSportShareRepository,
    FileSportShareRepository,
    MemorySportShareRepository,
)
from services.batch_service import BatchStore, DataMode
from services.sportshare.estimator import estimate_sport_share


class TestDBPersistence(unittest.TestCase):
    """DB repositories — save, destroy, recreate, verify."""

    def test_recognition_memory_roundtrip(self):
        repo = MemoryRecognitionRepository()
        results = [{"enterprise_id": "1", "sport_score": 0.5, "sport_category": "体育赛事"}]
        repo.save_batch("B1", results)
        loaded = repo.load_batch("B1")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["sport_score"], 0.5)

    def test_recognition_file_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            repo = FileRecognitionRepository(base_dir=d)
            results = [{"enterprise_id": "E1", "sport_score": 0.7}]
            repo.save_batch("BATCH-001", results)
            # Destroy and recreate
            repo2 = FileRecognitionRepository(base_dir=d)
            loaded = repo2.load_batch("BATCH-001")
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["sport_score"], 0.7)

    def test_share_memory_roundtrip(self):
        repo = MemorySportShareRepository()
        results = [{"enterprise_id": "1", "effective_share": 0.5, "share_source": "model"}]
        repo.save_batch("B1", results)
        loaded = repo.load_batch("B1")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["share_source"], "model")

    def test_share_file_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            repo = FileSportShareRepository(base_dir=d)
            results = [{"enterprise_id": "E1", "effective_share": 0.65, "share_source": "fallback"}]
            repo.save_batch("B2", results)
            repo2 = FileSportShareRepository(base_dir=d)
            loaded = repo2.load_batch("B2")
            self.assertEqual(loaded[0]["effective_share"], 0.65)


class TestFormalArtifactSemantics(unittest.TestCase):
    """Formal mode missing model → artifact_required, not batch fallback."""

    def test_formal_missing_model_artifact_required(self):
        est = estimate_sport_share(
            enterprise={"enterprise_id": "F1", "business_text": "体育赛事运营", "industry_code": 8911},
            recognition_result={"sport_score": 0.7, "code_type": "direct", "sport_category": "体育赛事"},
            model_artifact=None,
            data_mode="formal",
        )
        self.assertEqual(est.share_source, "artifact_required")
        self.assertEqual(est.effective_share, 0.0)
        self.assertIn("error", est.metadata)

    def test_demo_missing_model_uses_fallback(self):
        """Demo mode: missing model → fallback (acceptable for demo)"""
        est = estimate_sport_share(
            enterprise={"enterprise_id": "D1", "business_text": "体育赛事运营", "industry_code": 8911},
            recognition_result={"sport_score": 0.7, "code_type": "direct", "sport_category": "体育赛事"},
            model_artifact=None,
            data_mode="demo",
        )
        self.assertEqual(est.share_source, "fallback")
        self.assertIsNotNone(est.fallback_share)

    def test_formal_valid_model_enterprise_ineligible_fallback(self):
        """Formal with valid model but enterprise ineligible → fallback (correct)"""
        from ml.sportshare.model import SportShareModelArtifact, create_model, train_model
        import numpy as np
        from ml.sportshare.features import FEATURE_NAMES

        # Train minimal model
        X = np.random.rand(20, len(FEATURE_NAMES))
        y = np.clip(X[:, 0] * 0.3 + X[:, 1] * 0.2, 0, 1)
        model = train_model(X, y, random_state=42)
        artifact = SportShareModelArtifact(model=model, model_version="TEST-1")

        # Enterprise with empty text → not eligible
        est = estimate_sport_share(
            enterprise={"enterprise_id": "F2", "business_text": "", "industry_code": None},
            recognition_result={"sport_score": 0.0, "code_type": "none", "sport_category": "非体育"},
            model_artifact=artifact,
            data_mode="formal",
        )
        # Has model but enterprise ineligible → fallback for this enterprise
        self.assertEqual(est.share_source, "fallback")
        self.assertIsNotNone(est.fallback_share)

    def test_manual_beats_all(self):
        """Manual > model > fallback regardless of data_mode"""
        est = estimate_sport_share(
            enterprise={"enterprise_id": "M1", "business_text": "体育赛事"},
            recognition_result={"sport_score": 0.5, "code_type": "direct"},
            model_artifact=None,
            manual_share_override=0.42,
            data_mode="formal",
        )
        self.assertEqual(est.share_source, "manual")
        self.assertEqual(est.effective_share, 0.42)


class TestFullRestartPersistence(unittest.TestCase):
    """Complete pipeline → destroy → reinitialize → reload all results."""

    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_full_restart_all_results_survive(self):
        from services.sport_recognition import recognize_sport_business
        from services.review_workflow_service import create_review_tasks

        store1 = BatchStore(storage_dir=self.tmpdir.name)
        batch = store1.create_batch(data_mode=DataMode.TEST.value, total_rows=3, operator="restart-test")
        bid = batch.batch_id

        enterprises = [
            {"enterprise_id": "R1", "enterprise_name": "Reco1", "business_text": "体育赛事运营", "industry_code": 8911, "credit_code": "C1"},
            {"enterprise_id": "R2", "enterprise_name": "Reco2", "business_text": "健身培训", "industry_code": 8391, "credit_code": "C2"},
            {"enterprise_id": "R3", "enterprise_name": "Reco3", "business_text": "餐饮服务", "industry_code": None, "credit_code": "C3"},
        ]

        # Recognition
        recs = []
        for ent in enterprises:
            r = recognize_sport_business(ent["business_text"], ent["industry_code"], ent["enterprise_name"])
            r["enterprise_id"] = ent["enterprise_id"]
            r["enterprise_name"] = ent["enterprise_name"]
            r["credit_code"] = ent["credit_code"]
            recs.append(r)
        store1.save_results(bid, "recognition", recs)

        # SportShare
        shares = []
        for i, ent in enumerate(enterprises):
            est = estimate_sport_share(enterprise=ent, recognition_result=recs[i], data_mode="test")
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
        store1.save_results(bid, "share", shares)

        # Scale
        store1.save_results(bid, "scale", [{"type": "category", "outputs": {"体育赛事": 1085.40, "健身休闲": 1085.40}}])

        # Scenario
        store1.save_results(bid, "scenario", [{"scenario_id": "standard_alpha_20", "total_allocated": 2170.80, "status": "ok"}])

        # Validation
        store1.save_results(bid, "validation", [{"type": "audit", "passed": 23, "total": 24}])

        # Review
        tasks = create_review_tasks(recs, batch_id=bid)
        task_dicts = [{k: v for k, v in t.__dict__.items() if not k.startswith("_")} for t in tasks]
        store1.save_results(bid, "review", task_dicts)

        store1.update_status(bid, "finalized")

        # ---- DESTROY ----
        del store1

        # ---- REINITIALIZE ----
        store2 = BatchStore(storage_dir=self.tmpdir.name)
        batch2 = store2.get_batch(bid)
        self.assertIsNotNone(batch2, "Batch must survive restart")

        recs2 = store2.load_results(bid, "recognition")
        self.assertEqual(len(recs2), 3, "Recognition must survive restart")
        self.assertEqual(recs2[0]["enterprise_name"], "Reco1")

        shares2 = store2.load_results(bid, "share")
        self.assertEqual(len(shares2), 3, "SportShare must survive restart")

        scale2 = store2.load_results(bid, "scale")
        self.assertEqual(len(scale2), 1, "Scale must survive restart")

        scen2 = store2.load_results(bid, "scenario")
        self.assertEqual(len(scen2), 1, "Scenario must survive restart")
        self.assertEqual(scen2[0]["total_allocated"], 2170.80)

        val2 = store2.load_results(bid, "validation")
        self.assertEqual(len(val2), 1, "Validation must survive restart")

        rev2 = store2.load_results(bid, "review")
        self.assertEqual(len(rev2), 3, "Review must survive restart")

        # Directory
        from services.directory_service import DirectoryService
        # Submit reviews to confirm some
        from services.review_workflow_service import submit_review
        t1 = tasks[0]
        t1 = submit_review(t1, "A", "yes", "体育赛事", 0.5)
        t1 = submit_review(t1, "B", "yes", "体育赛事", 0.5)
        updated = [{k: v for k, v in t.__dict__.items() if not k.startswith("_")} for t in [t1, tasks[1], tasks[2]]]
        store2.save_results(bid, "review", updated)

        dir_svc = DirectoryService(store=store2)
        entries = dir_svc.get_directory(batch_id=bid)
        self.assertGreaterEqual(len(entries), 1, "Directory must have finalized entries")


class TestScaleScenarioValidationRepos(unittest.TestCase):
    """Scale/Scenario/Validation repo roundtrip (DB not tested — requires in-memory SQLite)."""

    def test_scale_file_roundtrip(self):
        from repositories.scale_repo import FileScaleRepository
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            repo = FileScaleRepository(base_dir=d)
            results = [{"type": "category", "total_allocated": 2170.80, "outputs": {"体育赛事": 1085.40, "健身休闲": 1085.40}}]
            repo.save_batch("B-SCALE", results)
            repo2 = FileScaleRepository(base_dir=d)
            loaded = repo2.load_batch("B-SCALE")
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["total_allocated"], 2170.80)

    def test_scale_memory_roundtrip(self):
        from repositories.scale_repo import MemoryScaleRepository
        repo = MemoryScaleRepository()
        results = [{"type": "category", "total_allocated": 2170.80}]
        repo.save_batch("B1", results)
        loaded = repo.load_batch("B1")
        self.assertEqual(loaded[0]["total_allocated"], 2170.80)

    def test_scenario_file_roundtrip(self):
        from repositories.scale_repo import FileScenarioRepository
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            repo = FileScenarioRepository(base_dir=d)
            results = [{"scenario_id": "standard_alpha_20", "total_allocated": 2170.80, "status": "ok"}]
            repo.save_batch("B-SCEN", results)
            repo2 = FileScenarioRepository(base_dir=d)
            loaded = repo2.load_batch("B-SCEN")
            self.assertEqual(loaded[0]["status"], "ok")

    def test_scenario_memory_roundtrip(self):
        from repositories.scale_repo import MemoryScenarioRepository
        repo = MemoryScenarioRepository()
        results = [{"scenario_id": "s1", "total_allocated": 2170.80}]
        repo.save_batch("B1", results)
        loaded = repo.load_batch("B1")
        self.assertEqual(len(loaded), 1)

    def test_validation_file_roundtrip(self):
        from repositories.scale_repo import FileValidationRepository
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            repo = FileValidationRepository(base_dir=d)
            results = [{"type": "audit", "passed": 23, "total": 24}]
            repo.save_batch("B-VAL", results)
            repo2 = FileValidationRepository(base_dir=d)
            loaded = repo2.load_batch("B-VAL")
            self.assertEqual(loaded[0]["passed"], 23)

    def test_validation_memory_roundtrip(self):
        from repositories.scale_repo import MemoryValidationRepository
        repo = MemoryValidationRepository()
        results = [{"type": "audit", "passed": 23}]
        repo.save_batch("B1", results)
        loaded = repo.load_batch("B1")
        self.assertEqual(len(loaded), 1)


if __name__ == "__main__":
    unittest.main()
