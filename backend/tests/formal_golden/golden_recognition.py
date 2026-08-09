"""
Golden Regression — recognition boundary, candidate counts, validation.

Formal artifact dependent. SKIP if missing — no synthetic data generation.
"""

import json
import unittest
from pathlib import Path

import pytest


def _find_artifact(glob_pattern: str) -> Path | None:
    matches = sorted(Path(".").glob(glob_pattern))
    return matches[-1] if matches else None


def _load_csv(path: Path) -> list[dict]:
    import csv
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


class TestGoldenRecognitionBoundary(unittest.TestCase):
    """Golden regression for 76,687 full-sample candidate counts."""

    @pytest.mark.formal_artifact
    def test_full_sample_row_count(self):
        """76,687 total rows in formal dataset."""
        path = _find_artifact("data/**/enterprise_dataset_*.csv")
        if path is None:
            self.skipTest("Formal enterprise dataset artifact missing")
        rows = _load_csv(path)
        self.assertEqual(len(rows), 76687, f"Expected 76687 rows, got {len(rows)}")

    @pytest.mark.formal_artifact
    def test_sportfusion_candidate_count(self):
        """SportFusion识别: 8,950 candidates."""
        path = _find_artifact("data/**/sport_ratio_results_*.csv")
        if path is None:
            self.skipTest("Formal sport_ratio_results artifact missing")
        rows = _load_csv(path)
        # Find the '是否体育' or 'is_sport' column
        sport_col = None
        for col in ["是否体育", "is_sport"]:
            if col in (rows[0] if rows else {}):
                sport_col = col
                break
        if sport_col:
            sport = [r for r in rows if r.get(sport_col) in ("是", "True", "1", "yes")]
        else:
            # Fallback: check ratio column
            ratio_cols = [c for c in rows[0].keys() if '占比' in c or 'ratio' in c or 'score' in c]
            ratio_col = ratio_cols[0] if ratio_cols else None
            if ratio_col:
                sport = [r for r in rows if r.get(ratio_col) and float(r[ratio_col]) > 0]
            else:
                self.skipTest("Cannot determine sport candidate column")
        self.assertEqual(len(sport), 8950, f"Expected 8950, got {len(sport)}")

    @pytest.mark.formal_artifact
    def test_traditional_code_count(self):
        """传统直接代码: 8,016 (from dataset)."""
        path = _find_artifact("data/**/enterprise_dataset_*.csv")
        if path is None:
            self.skipTest("Formal dataset missing")
        rows = _load_csv(path)
        from domain.industry_code import normalize_industry_code
        from utils.industry_code import is_direct_sport_code
        direct = sum(1 for r in rows if r.get("行业代码") and is_direct_sport_code(normalize_industry_code(r["行业代码"])))
        self.assertEqual(direct, 8016, f"Expected 8016, got {direct}")

    @pytest.mark.formal_artifact
    def test_crossover_candidate_count(self):
        """跨界候选: 977."""
        path = _find_artifact("data/**/sport_ratio_results_*.csv")
        if path is None:
            self.skipTest("Formal sport_ratio_results missing")
        rows = _load_csv(path)
        crossovers = [r for r in rows if r.get("跨界类型") and r["跨界类型"].strip()]
        self.assertEqual(len(crossovers), 977, f"Expected 977, got {len(crossovers)}")


class TestGoldenRecognitionValidation(unittest.TestCase):
    """Golden regression for recognition validation metrics."""

    @pytest.mark.formal_artifact
    def test_model_validation_metrics_exist(self):
        """Validation metrics file exists and has expected structure."""
        path = _find_artifact("data/**/model_validation*.json")
        if path is None:
            path = _find_artifact("submission/**/model_validation*.json")
        if path is None:
            self.skipTest("Formal model_validation artifact missing")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)
        # Key may be 'sport_ratio_pct' or 'sport_ratio_pct' in Chinese context
        self.assertTrue(any(k for k in data if 'ratio' in k or 'score' in k or 'count' in k),
                        f"No recognizable metric keys in: {list(data.keys())[:5]}")

    @pytest.mark.formal_artifact
    def test_validation_avg_sport_score(self):
        """SportScore均值: ~0.6471."""
        path = _find_artifact("data/**/model_validation*.json")
        if path is None:
            path = _find_artifact("submission/**/model_validation*.json")
        if path is None:
            self.skipTest("Formal validation missing")
        data = json.loads(path.read_text(encoding="utf-8"))
        avg = data.get("avg_sport_ratio", data.get("average_sport_ratio_pct_among_sport_enterprises", 0))
        if avg == 0 and "avg_sport_ratio" not in data:
            avg = data.get("avg_sport_ratio_pct", 0) / 100.0 if data.get("avg_sport_ratio_pct") else 0
        if avg > 0:
            self.assertAlmostEqual(avg, 0.6471, places=2,
                                   msg=f"avg_sport_ratio={avg:.4f}, expected ~0.6471")
        else:
            self.skipTest("avg_sport_ratio not found in validation artifact")


class TestGoldenReferenceLabels(unittest.TestCase):
    """Golden regression for reference label validation (300 samples)."""

    @pytest.mark.formal_artifact
    def test_reference_labels_available(self):
        """At minimum, note whether reference labels exist."""
        from services.validation_service import compute_binary_metrics

        # Check if formal 300 labels exist anywhere
        paths = list(Path(".").glob("**/reference_labels*.json")) + \
                list(Path(".").glob("**/gold_standard*.csv"))
        if not paths:
            self.skipTest("Formal reference labels (300) not found — Golden validation SKIPPED")

        # Validate structure (JSON or CSV)
        p = Path(paths[0])
        if p.suffix == '.csv':
            import csv
            with open(p, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            self.assertGreater(len(rows), 0, "Reference label CSV is empty")
            self.assertIn(len(rows), [285, 300], f"Expected 285 or 300 labels, got {len(rows)}")
        else:
            try:
                data = json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception:
                data = json.loads(p.read_text(encoding="utf-8"))
            self.assertIsInstance(data, (dict, list))


if __name__ == "__main__":
    unittest.main()
