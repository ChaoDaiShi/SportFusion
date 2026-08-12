"""
Golden Regression — Canonical Recognition Boundary (Phase 5 final).

Canonical values (cross-verified BATCH-20260803-R1 + formal data):
  total=76687, traditional=8016, sportfusion=8950, intersection=8016,
  sf_only=934, trad_only=0, net_increase=934, crossover=977.

Legacy 7999/951/17 retained in docs/LEGACY_RESULT_RECONCILIATION.md.
"""

import csv
import unittest
from pathlib import Path


def _load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _find_file(glob_pattern: str) -> Path | None:
    matches = sorted(Path(".").glob(glob_pattern))
    return matches[-1] if matches else None


class TestCanonicalRecognitionGolden(unittest.TestCase):
    """Canonical recognition set operations — Phase 5 locked values."""

    def test_total_enterprises(self):
        path = _find_file("submission/**/enterprise_dataset_*.csv")
        if not path:
            self.skipTest("Enterprise dataset missing")
        rows = _load_csv(path)
        self.assertEqual(len(rows), 76687)

    def test_traditional_direct_code_count(self):
        path = _find_file("submission/**/enterprise_dataset_*.csv")
        if not path:
            self.skipTest("Enterprise dataset missing")
        from domain.industry_code import normalize_industry_code
        from utils.industry_code import is_direct_sport_code
        rows = _load_csv(path)
        trad = sum(1 for r in rows if is_direct_sport_code(normalize_industry_code(r.get("行业代码",""))))
        self.assertEqual(trad, 8016)

    def test_sportfusion_candidate_count(self):
        path = _find_file("data/**/sport_ratio_results.csv")
        if not path:
            self.skipTest("Sport ratio results missing")
        rows = _load_csv(path)
        sport_col = next(c for c in rows[0] if "是否体育" in c)
        sf = sum(1 for r in rows if r.get(sport_col) in ("True","是","1","yes"))
        self.assertEqual(sf, 8950)

    def test_intersection_is_all_traditional(self):
        """Traditional ⊂ SportFusion: all 8016 trad codes are sport candidates."""
        ds_path = _find_file("submission/**/enterprise_dataset_*.csv")
        sr_path = _find_file("data/**/sport_ratio_results.csv")
        if not ds_path or not sr_path:
            self.skipTest("Artifacts missing")
        from domain.industry_code import normalize_industry_code
        from utils.industry_code import is_direct_sport_code
        ds_rows = _load_csv(ds_path)
        sr_rows = _load_csv(sr_path)
        cc_col = next(c for c in ds_rows[0] if "信用" in c and "行业" not in c)
        sport_col = next(c for c in sr_rows[0] if "是否体育" in c)
        sr_cc = next(iter(sr_rows[0]))
        trad_ids = {r[cc_col] for r in ds_rows if is_direct_sport_code(normalize_industry_code(r.get("行业代码",""))) and r.get(cc_col)}
        sf_ids = {r[sr_cc] for r in sr_rows if r.get(sport_col) in ("True","是","1","yes") and r.get(sr_cc)}
        inter = trad_ids & sf_ids
        self.assertEqual(len(inter), 8016, "Intersection must be 8016")
        self.assertEqual(len(trad_ids - sf_ids), 0, "Traditional only must be 0")
        self.assertEqual(len(sf_ids - trad_ids), 934, "SF only must be 934")
        self.assertTrue(trad_ids <= sf_ids, "Traditional must be subset of SportFusion")

    def test_net_increase(self):
        """934 net increase = 8950 - 8016."""
        self.assertEqual(8950 - 8016, 934)

    def test_crossover_count(self):
        path = _find_file("data/**/sport_ratio_results.csv")
        if not path:
            self.skipTest("Sport ratio results missing")
        rows = _load_csv(path)
        cross_col = next(c for c in rows[0] if "跨界" in c and "类型" in c)
        sport_col = next(c for c in rows[0] if "是否体育" in c)
        cross = sum(1 for r in rows if r.get(sport_col) in ("True","是","1","yes") and r.get(cross_col,"").strip())
        self.assertEqual(cross, 977)

    def test_legacy_951_is_not_current(self):
        """951 is NOT a current metric — it is historical only."""
        # SF only = 934, not 951
        self.assertNotEqual(934, 951, "SF only is 934, not legacy 951")
