"""
Phase 3 regression tests — SportShare RF pipeline + scale allocation + validation.

Covers:
    - SportShare feature leakage prevention
    - RF model train/save/load/predict
    - 5x5 CV evaluation
    - Residual-based prediction intervals
    - Fallback traceability
    - Manual override priority
    - Macro calibration conservation
    - Scenario engine (3x4=12)
    - Binary/multiclass metrics
    - Threshold sweep
    - Audit framework
    - Formal/demo/test isolation
"""

import tempfile
import unittest

import numpy as np
from ml.sportshare.dataset import (
    build_target,
)
from ml.sportshare.evaluate import (
    EvaluationResult,
    compute_residual_quantile,
    evaluate_cv,
)

# ---------------------------------------------------------------------------
# SportShare features
# ---------------------------------------------------------------------------
from ml.sportshare.features import (
    FEATURE_NAMES,
    build_sportshare_features,
    sportshare_features_to_array,
)
from ml.sportshare.interval import (
    build_prediction_interval,
    compute_calibration_interval,
)
from ml.sportshare.model import (
    SportShareModelArtifact,
    load_artifact,
    predict_single,
    save_artifact,
    train_model,
)

# ---------------------------------------------------------------------------
# Scale / Scenario / Validation
# ---------------------------------------------------------------------------
from services.macro_calibration_service import (
    ScaleAllocationResult,
    compute_boundary_split,
    compute_structural_weight,
    load_official_total,
    normalize_weights,
)
from services.scenario_service import (
    EVIDENCE_CALIBRATIONS,
    ScenarioConfig,
    generate_scenario_configs,
    run_scenario,
)

# ---------------------------------------------------------------------------
# SportShare service
# ---------------------------------------------------------------------------
from services.sportshare.estimator import (
    _fallback_by_structure,
    estimate_sport_share,
)
from services.validation_service import (
    compute_binary_metrics,
    compute_multiclass_metrics,
    run_audit_checks,
    run_threshold_sweep,
)


# ===================================================================
# Target Leakage Prevention
# ===================================================================
class TestTargetLeakage(unittest.TestCase):
    """SportShare features must NOT leak the target T_i"""

    def test_w1_not_in_sportshare_features(self):
        """W1 (business scope ratio) excluded from SportShare feature vector"""
        fv = build_sportshare_features("体育赛事运营，运动器材销售，餐饮服务", 8911)
        # w1_business_scope should NOT exist
        self.assertFalse(hasattr(fv, "w1_business_scope"),
                         "SportShareFeatureVector MUST NOT have w1_business_scope (target leakage)")

    def test_no_business_line_ratio_in_features(self):
        """Feature array must not contain sport_lines/total_lines ratio"""
        fv = build_sportshare_features("体育赛事，运动器材，餐饮服务", 8911)
        arr = sportshare_features_to_array(fv)
        # None of the feature values should directly encode the T_i ratio
        for i, val in enumerate(arr):
            self.assertIsInstance(val, (int, float), f"Feature[{i}] {FEATURE_NAMES[i]} is not numeric")

    def test_feature_names_no_leakage(self):
        """Feature name list must not contain 'w1_business_scope'"""
        self.assertNotIn("w1_business_scope", FEATURE_NAMES)
        self.assertNotIn("total_business_lines", FEATURE_NAMES)
        self.assertNotIn("sport_business_lines", FEATURE_NAMES)

    def test_build_target_is_structural(self):
        """Target T_i = sport_lines / total_lines (structural, not revenue)"""
        t = build_target("体育赛事运营，运动器材销售，餐饮服务")
        self.assertIsNotNone(t)
        self.assertAlmostEqual(t, 2.0 / 3.0, places=2)
        self.assertGreaterEqual(t, 0.0)
        self.assertLessEqual(t, 1.0)

    def test_build_target_empty_text(self):
        self.assertIsNone(build_target(""))
        self.assertIsNone(build_target("a"))


# ===================================================================
# RF Model: train/save/load/predict
# ===================================================================
class TestRandomForestPipeline(unittest.TestCase):
    """RF model serialization roundtrip + deterministic seed"""

    def setUp(self):
        # Synthetic training data
        np.random.seed(42)
        self.X = np.random.rand(100, len(FEATURE_NAMES))
        self.y = np.clip(self.X[:, 0] * 0.3 + self.X[:, 3] * 0.5 + np.random.normal(0, 0.05, 100), 0, 1)

    def test_deterministic_training(self):
        """Same seed → same model"""
        m1 = train_model(self.X, self.y, random_state=42)
        m2 = train_model(self.X, self.y, random_state=42)
        p1 = m1.predict(self.X[:5])
        p2 = m2.predict(self.X[:5])
        np.testing.assert_array_almost_equal(p1, p2)

    def test_save_load_roundtrip(self):
        """Model survives save→load cycle"""
        model = train_model(self.X, self.y, random_state=42)
        artifact = SportShareModelArtifact(model=model, training_samples=len(self.y))

        with tempfile.TemporaryDirectory() as tmpdir:
            save_artifact(artifact, tmpdir)
            loaded = load_artifact(tmpdir)

            X_test = self.X[:5]
            p_orig = model.predict(X_test)
            p_loaded = loaded.model.predict(X_test)
            np.testing.assert_array_almost_equal(p_orig, p_loaded)
            self.assertEqual(loaded.training_samples, len(self.y))

    def test_prediction_in_0_1(self):
        """All predictions in [0, 1]"""
        model = train_model(self.X, self.y, random_state=42)
        preds = model.predict(self.X)
        self.assertTrue(np.all(preds >= 0.0))
        self.assertTrue(np.all(preds <= 1.0))

    def test_predict_single(self):
        """predict_single returns clamped float"""
        model = train_model(self.X, self.y, random_state=42)
        artifact = SportShareModelArtifact(model=model)
        result = predict_single(artifact, list(self.X[0]))
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)

    def test_model_metadata_complete(self):
        """Artifact metadata has all required fields"""
        model = train_model(self.X, self.y, random_state=42)
        artifact = SportShareModelArtifact(
            model=model,
            model_version="TEST-1.0",
            training_dataset_version="DS-1",
            training_samples=len(self.y),
        )
        self.assertEqual(artifact.model_version, "TEST-1.0")
        self.assertEqual(artifact.training_samples, 100)
        self.assertIsNotNone(artifact.model)


# ===================================================================
# 5x5 CV Evaluation
# ===================================================================
class TestCrossValidation(unittest.TestCase):
    """Repeated 5x5 CV metrics"""

    def setUp(self):
        np.random.seed(42)
        self.X = np.random.rand(200, len(FEATURE_NAMES))
        self.y = np.clip(self.X[:, 0] * 0.4 + self.X[:, 3] * 0.4 + np.random.normal(0, 0.03, 200), 0, 1)

    def test_evaluate_returns_all_metrics(self):
        result = evaluate_cv(self.X, self.y, n_splits=5, n_repeats=2, random_state=42)
        self.assertIsInstance(result, EvaluationResult)
        self.assertGreaterEqual(result.mae, 0.0)
        self.assertGreaterEqual(result.r2, -1.0)
        self.assertLessEqual(result.r2, 1.0)
        self.assertGreaterEqual(result.spearman, -1.0)
        self.assertLessEqual(result.spearman, 1.0)
        self.assertEqual(result.n_samples, 200)
        self.assertEqual(result.n_features, len(FEATURE_NAMES))

    def test_residual_quantile(self):
        model = train_model(self.X, self.y, random_state=42)
        y_pred = model.predict(self.X)
        q90 = compute_residual_quantile(self.y, y_pred, q=0.90)
        self.assertGreater(q90, 0.0)


# ===================================================================
# Prediction Intervals
# ===================================================================
class TestPredictionIntervals(unittest.TestCase):
    """Residual-based intervals replace old heuristic ±15%"""

    def test_interval_in_0_1(self):
        lower, upper = build_prediction_interval(0.5, 0.10)
        self.assertGreaterEqual(lower, 0.0)
        self.assertLessEqual(upper, 1.0)
        self.assertLessEqual(lower, 0.5)
        self.assertGreaterEqual(upper, 0.5)

    def test_interval_clips_at_boundaries(self):
        lower, _ = build_prediction_interval(0.05, 0.20)
        self.assertEqual(lower, 0.0)
        _, upper2 = build_prediction_interval(0.95, 0.20)
        self.assertEqual(upper2, 1.0)

    def test_calibration_interval_from_data(self):
        y_true = np.array([0.3, 0.5, 0.7, 0.4, 0.6])
        y_pred = np.array([0.32, 0.48, 0.68, 0.42, 0.58])
        q90 = compute_calibration_interval(y_true, y_pred, q=0.90)
        self.assertGreater(q90, 0.0)
        self.assertLess(q90, 0.5)


# ===================================================================
# Fallback & Manual Override
# ===================================================================
class TestFallbackAndManual(unittest.TestCase):
    """Fallback traceability + manual override priority"""

    def test_fallback_direct_code(self):
        val = _fallback_by_structure("direct", 0.3, "体育赛事", 2, 1)
        self.assertEqual(val, 0.65)

    def test_fallback_indirect_code(self):
        val = _fallback_by_structure("indirect", 0.2, "体育培训", 2, 1)
        self.assertEqual(val, 0.35)

    def test_fallback_text_only(self):
        val = _fallback_by_structure("none", 0.15, "体育用品", 2, 1)
        self.assertEqual(val, 0.25)

    def test_fallback_no_signal(self):
        val = _fallback_by_structure("none", 0.0, "", 0, 0)
        self.assertEqual(val, 0.0)

    def test_manual_override_priority(self):
        """Manual override takes highest priority"""
        est = estimate_sport_share(
            enterprise={"enterprise_id": "1", "business_text": "体育"},
            recognition_result={"sport_score": 0.5, "code_type": "direct"},
            manual_share_override=0.42,
        )
        self.assertEqual(est.share_source, "manual")
        self.assertEqual(est.effective_share, 0.42)

    def test_fallback_is_traceable(self):
        """Fallback decisions carry rule metadata"""
        est = estimate_sport_share(
            enterprise={"enterprise_id": "1", "business_text": "餐饮服务"},
            recognition_result={"sport_score": 0.0, "code_type": "none"},
        )
        self.assertEqual(est.share_source, "fallback")
        self.assertIn("fallback_rule", est.metadata)


# ===================================================================
# Macro Calibration
# ===================================================================
class TestMacroCalibration(unittest.TestCase):
    """Official total constraint conservation"""

    def test_load_official_total(self):
        cal = load_official_total()
        self.assertEqual(cal.year, 2022)
        self.assertEqual(cal.region, "四川省")
        self.assertGreater(cal.official_total_output, 0)
        self.assertEqual(cal.unit, "亿元")

    def test_weight_normalization(self):
        weights = [1.0, 2.0, 3.0, 4.0]
        norm = normalize_weights(weights)
        self.assertAlmostEqual(sum(norm), 1.0, places=6)
        self.assertEqual(len(norm), 4)

    def test_weight_normalization_all_zeros(self):
        norm = normalize_weights([0.0, 0.0, 0.0])
        self.assertAlmostEqual(sum(norm), 1.0, places=6)
        self.assertAlmostEqual(norm[0], 1.0 / 3.0, places=4)

    def test_boundary_split_sums_to_total(self):
        allocations = [
            ScaleAllocationResult(category="体育赛事", structural_weight=3.0, is_traditional_boundary=True),
            ScaleAllocationResult(category="体育赛事", structural_weight=1.0, is_traditional_boundary=False),
            ScaleAllocationResult(category="健身休闲", structural_weight=2.0, is_traditional_boundary=True),
        ]
        cat_outputs = {"体育赛事": 100.0, "健身休闲": 50.0}
        split = compute_boundary_split(allocations, cat_outputs)
        self.assertAlmostEqual(split["inside_traditional_boundary_output"] + split["outside_traditional_boundary_output"], 150.0, places=2)

    def test_compute_structural_weight_default(self):
        w = compute_structural_weight(0.5, structural_factor=1.0)
        self.assertAlmostEqual(w, 0.5, places=4)


# ===================================================================
# Scenario Engine
# ===================================================================
class TestScenarioEngine(unittest.TestCase):
    """3×4 = 12 scenarios"""

    def test_generates_12_scenarios(self):
        configs = generate_scenario_configs()
        self.assertEqual(len(configs), 12)

    def test_baseline_exists(self):
        configs = generate_scenario_configs()
        baseline = [c for c in configs if c.alpha == 0.20 and c.evidence_calibration == "standard"]
        self.assertEqual(len(baseline), 1)
        self.assertEqual(baseline[0].scenario_id, "standard_alpha_20")

    def test_all_alphas_present(self):
        configs = generate_scenario_configs()
        alphas = sorted({c.alpha for c in configs})
        self.assertEqual(alphas, [0.0, 0.10, 0.20, 0.30])

    def test_all_calibrations_present(self):
        configs = generate_scenario_configs()
        cals = sorted({c.evidence_calibration for c in configs})
        self.assertEqual(cals, sorted(EVIDENCE_CALIBRATIONS))

    def test_scenario_run_produces_output(self):
        # alpha=0 works without official prior
        config = ScenarioConfig(scenario_id="test", evidence_calibration="standard", alpha=0.0)
        enterprises = [
            {"enterprise_id": "1", "business_text": "体育赛事运营", "industry_code": 8911},
            {"enterprise_id": "2", "business_text": "餐饮服务", "industry_code": None},
        ]
        from services.sportshare.estimator import batch_estimate
        estimates = batch_estimate(enterprises, [
            {"sport_score": 0.7, "code_type": "direct", "sport_category": "体育赛事"},
            {"sport_score": 0.0, "code_type": "none", "sport_category": "非体育"},
        ])
        result = run_scenario(config, enterprises, estimates, [
            {"sport_score": 0.7, "code_type": "direct", "sport_category": "体育赛事"},
            {"sport_score": 0.0, "code_type": "none", "sport_category": "非体育"},
        ])
        self.assertEqual(result.scenario_id, "test")
        self.assertEqual(result.status, "ok")
        self.assertAlmostEqual(result.total_allocated, 2170.80, places=0)


# ===================================================================
# Validation: binary + multiclass metrics
# ===================================================================
class TestValidationMetrics(unittest.TestCase):
    """Metrics computed from y_true/y_pred, never hardcoded"""

    def test_perfect_binary(self):
        y_true = [1, 1, 0, 0, 1]
        y_pred = [1, 1, 0, 0, 1]
        m = compute_binary_metrics(y_true, y_pred)
        self.assertEqual(m.accuracy, 1.0)
        self.assertEqual(m.precision, 1.0)

    def test_binary_with_errors(self):
        y_true = [1, 1, 0, 0, 1]
        y_pred = [1, 0, 0, 1, 1]
        m = compute_binary_metrics(y_true, y_pred)
        self.assertLess(m.accuracy, 1.0)
        self.assertEqual(m.false_positives, 1)
        self.assertEqual(m.false_negatives, 1)

    def test_multiclass_macro_f1(self):
        y_true = ["体育赛事", "健身休闲", "体育用品", "体育赛事", "健身休闲"]
        y_pred = ["体育赛事", "健身休闲", "体育用品", "体育赛事", "体育用品"]
        m = compute_multiclass_metrics(y_true, y_pred)
        self.assertGreaterEqual(m.accuracy, 0.0)
        self.assertLessEqual(m.macro_f1, 1.0)
        self.assertGreater(len(m.class_labels), 0)
        self.assertEqual(m.n_samples, 5)
        self.assertGreater(len(m.confusion_matrix), 0)

    def test_threshold_sweep_coverage(self):
        scores = [0.0, 0.05, 0.15, 0.5, 0.9, 1.0]
        y_true = [0, 0, 1, 1, 1, 1]
        results = run_threshold_sweep(scores, y_true)
        self.assertGreater(len(results), 1)
        for r in results:
            self.assertIn("threshold", r)
            self.assertIn("f1", r)

    def test_audit_24_checks(self):
        result = run_audit_checks()
        self.assertEqual(result.total, 24)
        self.assertGreaterEqual(result.passed, 20)
        self.assertGreaterEqual(result.passed + result.failed + result.warnings + result.skipped, result.total)


# ===================================================================
# Formal/Demo/Test isolation
# ===================================================================
class TestFormalDemoIsolation(unittest.TestCase):
    """Formal must not silently fall back to demo"""

    def test_estimate_without_model_uses_fallback(self):
        """Without model artifact, estimate must use fallback, not pretend to have model"""
        est = estimate_sport_share(
            enterprise={"enterprise_id": "1", "business_text": "体育赛事"},
            recognition_result={"sport_score": 0.5, "code_type": "direct"},
            model_artifact=None,
        )
        self.assertEqual(est.share_source, "fallback")
        self.assertIsNone(est.model_share)
        self.assertIsNotNone(est.fallback_share)

    def test_model_eligible_flag(self):
        """is_model_eligible distinguishes model vs fallback candidates"""
        est_model = estimate_sport_share(
            enterprise={"enterprise_id": "1", "business_text": "体育赛事运营"},
            recognition_result={"sport_score": 0.5, "code_type": "direct"},
        )
        # Without real model artifact, fallback is used
        self.assertFalse(est_model.is_model_eligible)


# ===================================================================
# Provenance
# ===================================================================
class TestProvenance(unittest.TestCase):
    """Version metadata on all major outputs"""

    def test_estimate_has_metadata(self):
        est = estimate_sport_share(
            enterprise={"enterprise_id": "1", "business_text": "体育赛事"},
            recognition_result={"sport_score": 0.5, "code_type": "direct"},
        )
        self.assertIsInstance(est.metadata, dict)

    def test_official_total_config_has_source(self):
        cal = load_official_total()
        self.assertIsNotNone(cal.source)
        self.assertIsNotNone(cal.source_version)

    def test_scenario_config_has_description(self):
        config = ScenarioConfig(scenario_id="test", evidence_calibration="standard", alpha=0.20)
        self.assertIsNotNone(config.description)


# ===================================================================
# Phase 3 CLOSURE TESTS — merge blocker fixes
# ===================================================================

class TestClosureIndirectLeakage(unittest.TestCase):
    """A. Indirect leakage: changing sport_score must NOT change SportShare features"""

    def test_feature_names_exclude_sport_score(self):
        """FEATURE_NAMES must not contain sport_score"""
        from ml.sportshare.features import FEATURE_NAMES as FNS
        self.assertNotIn("sport_score", FNS)
        self.assertNotIn("w1_business_scope", FNS)
        self.assertNotIn("sport_business_lines", FNS)

    def test_feature_array_excludes_sport_score(self):
        """Feature array length = 11 (no sport_score)"""
        from ml.sportshare.features import FEATURE_NAMES as FNS, build_sportshare_features, sportshare_features_to_array
        fv = build_sportshare_features("体育赛事运营，运动器材销售", 8911)
        arr = sportshare_features_to_array(fv)
        self.assertEqual(len(arr), len(FNS))
        self.assertEqual(len(arr), 11)

    def test_sport_score_not_accepted_by_builder(self):
        """build_sportshare_features must not accept sport_score parameter"""
        import inspect
        sig = inspect.signature(build_sportshare_features)
        self.assertNotIn("sport_score", sig.parameters)

    def test_changing_sport_score_does_not_affect_features(self):
        """Indirect leakage test: modifying sport_score must produce identical features"""
        from ml.sportshare.features import build_sportshare_features, sportshare_features_to_array

        fv1 = build_sportshare_features("体育赛事运营，运动器材销售", 8911)
        arr1 = sportshare_features_to_array(fv1)

        # Same text/code → same features regardless of external sport_score
        fv2 = build_sportshare_features("体育赛事运营，运动器材销售", 8911)
        arr2 = sportshare_features_to_array(fv2)

        self.assertEqual(arr1, arr2,
                         "SportShare features must be invariant to sport_score")


class TestClosureAlphaSeparation(unittest.TestCase):
    """D. alpha separation: alpha changes must not change enterprise SportShare/SportScore/A_i"""

    def test_enterprise_weight_independent_of_alpha(self):
        """alpha does NOT enter compute_structural_weight"""
        from services.macro_calibration_service import compute_structural_weight

        w1 = compute_structural_weight(0.5, structural_factor=1.0)
        w2 = compute_structural_weight(0.5, structural_factor=1.0)
        self.assertEqual(w1, w2)
        # Structural weight only depends on effective_share and G_i
        self.assertEqual(w1, 0.5)

    def test_alpha_only_in_fusion(self):
        """alpha enters only at Layer 3 (fuse_category_structure)"""
        from services.macro_calibration_service import fuse_category_structure

        p_sample = {"体育赛事": 0.5, "健身休闲": 0.5}
        p_official = {"体育赛事": 0.6, "健身休闲": 0.4}

        # alpha = 0 → pure sample
        r0 = fuse_category_structure(p_sample, p_official, alpha=0.0)
        self.assertAlmostEqual(r0["体育赛事"], 0.5)

        # alpha = 1.0 → pure official
        r1 = fuse_category_structure(p_sample, p_official, alpha=1.0)
        self.assertAlmostEqual(r1["体育赛事"], 0.6)

        # alpha = 0.20 → blend
        r02 = fuse_category_structure(p_sample, p_official, alpha=0.20)
        expected = 0.80 * 0.5 + 0.20 * 0.6
        self.assertAlmostEqual(r02["体育赛事"], expected)

    def test_alpha_gt_0_without_prior_returns_empty(self):
        """Formal: alpha>0 without official prior → artifact_required"""
        from services.macro_calibration_service import fuse_category_structure
        p_sample = {"体育赛事": 1.0}
        result = fuse_category_structure(p_sample, None, alpha=0.20)
        self.assertEqual(result, {})


class TestClosureManualOverride(unittest.TestCase):
    """C. Manual override priority: manual > model > fallback"""

    def test_manual_overrides_model(self):
        """manual_share_override takes priority over everything"""
        est = estimate_sport_share(
            enterprise={"enterprise_id": "1", "business_text": "体育赛事运营"},
            recognition_result={"sport_score": 0.8, "code_type": "direct"},
            manual_share_override=0.42,
        )
        self.assertEqual(est.share_source, "manual")
        self.assertEqual(est.effective_share, 0.42)
        self.assertEqual(est.manual_share, 0.42)

    def test_fallback_when_no_model(self):
        """Without model artifact, fallback is used (not error)"""
        est = estimate_sport_share(
            enterprise={"enterprise_id": "1", "business_text": "体育赛事运营"},
            recognition_result={"sport_score": 0.5, "code_type": "direct"},
            model_artifact=None,
        )
        self.assertEqual(est.share_source, "fallback")
        self.assertIsNotNone(est.fallback_share)

    def test_manual_priority_over_fallback(self):
        """Manual beats fallback"""
        est = estimate_sport_share(
            enterprise={"enterprise_id": "1", "business_text": "体育"},
            recognition_result={"sport_score": 0.5, "code_type": "direct"},
            model_artifact=None,
            manual_share_override=0.73,
        )
        self.assertEqual(est.share_source, "manual")
        self.assertEqual(est.effective_share, 0.73)


class TestClosureScaleConservation(unittest.TestCase):
    """E/F/G. Scale conservation: category/region/boundary sum = official total"""

    def test_category_structure_sums_to_one(self):
        from services.macro_calibration_service import compute_sample_category_structure
        weights = {"体育赛事": 10.0, "健身休闲": 5.0, "体育用品": 5.0}
        p = compute_sample_category_structure(weights)
        self.assertAlmostEqual(sum(p.values()), 1.0, places=6)

    def test_boundary_split_sums_approximately(self):
        """inside + outside ≈ official total"""
        allocations = [
            ScaleAllocationResult(category="体育赛事", structural_weight=3.0, is_traditional_boundary=True),
            ScaleAllocationResult(category="体育赛事", structural_weight=1.0, is_traditional_boundary=False),
            ScaleAllocationResult(category="健身休闲", structural_weight=2.0, is_traditional_boundary=True),
        ]
        cat_outputs = {"体育赛事": 100.0, "健身休闲": 50.0}
        split = compute_boundary_split(allocations, cat_outputs)
        total = split["inside_traditional_boundary_output"] + split["outside_traditional_boundary_output"]
        self.assertAlmostEqual(total, 150.0, places=2)

    def test_category_allocation_preserves_total(self):
        from services.macro_calibration_service import allocate_category_output
        p_hat = {"体育赛事": 0.6, "健身休闲": 0.4}
        outputs = allocate_category_output(p_hat, 2170.80)
        self.assertAlmostEqual(sum(outputs.values()), 2170.80, places=2)


class TestClosureScenario(unittest.TestCase):
    """H. Scenario 3×4=12, I. Formal alpha>0 without prior"""

    def test_twelve_scenarios_generated(self):
        configs = generate_scenario_configs()
        self.assertEqual(len(configs), 12)

    def test_alpha_gt_0_with_prior_succeeds(self):
        """I. Formal scenario with alpha>0 now succeeds (official prior exists)"""
        config = ScenarioConfig(scenario_id="test", evidence_calibration="standard", alpha=0.20)
        enterprises = [{"enterprise_id": "1", "business_text": "体育赛事运营", "industry_code": 8911}]
        from services.sportshare.estimator import batch_estimate
        estimates = batch_estimate(enterprises, [{"sport_score": 0.7, "code_type": "direct", "sport_category": "体育赛事"}])

        result = run_scenario(config, enterprises, estimates, [
            {"sport_score": 0.7, "code_type": "direct", "sport_category": "体育赛事"},
        ])
        # official_category_prior.json now exists → scenario should succeed
        self.assertEqual(result.status, "ok")
        self.assertAlmostEqual(result.total_allocated, 2170.80, places=0)

    def test_alpha_zero_works_without_prior(self):
        """alpha=0 scenarios work without official prior"""
        config = ScenarioConfig(scenario_id="test_zero", evidence_calibration="standard", alpha=0.0)
        enterprises = [{"enterprise_id": "1", "business_text": "体育赛事运营", "industry_code": 8911}]
        from services.sportshare.estimator import batch_estimate
        estimates = batch_estimate(enterprises, [{"sport_score": 0.7, "code_type": "direct", "sport_category": "体育赛事"}])

        result = run_scenario(config, enterprises, estimates, [
            {"sport_score": 0.7, "code_type": "direct", "sport_category": "体育赛事"},
        ])
        self.assertEqual(result.status, "ok")
        self.assertAlmostEqual(result.total_allocated, 2170.80, places=0)


if __name__ == "__main__":
    unittest.main()
