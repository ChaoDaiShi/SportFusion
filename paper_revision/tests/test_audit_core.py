import unittest
import subprocess
import sys
from pathlib import Path

from paper_revision.audit_core import (
    classify_evidence,
    compute_snapshot_from_counts,
    concentration_metrics,
)


class AuditCoreTest(unittest.TestCase):
    def test_run_data_audit_can_be_loaded_by_path(self):
        script = Path(__file__).resolve().parents[1] / "run_data_audit.py"
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                f"import runpy; runpy.run_path(r'{script}', run_name='paper_revision_import_probe')",
            ],
            cwd=script.parent,
            capture_output=True,
            text=True,
        )
        self.assertEqual(probe.returncode, 0, probe.stderr)

    def test_snapshot_distinguishes_coverage_from_accuracy(self):
        snapshot = compute_snapshot_from_counts(
            total=100,
            traditional=10,
            fusion=12,
            crossover=3,
        )
        self.assertEqual(snapshot["traditional_coverage_pct"], 10.0)
        self.assertEqual(snapshot["fusion_coverage_pct"], 12.0)
        self.assertEqual(snapshot["relative_identification_increase_pct"], 20.0)
        self.assertNotIn("accuracy", snapshot)

    def test_evidence_grades_reject_conflicting_or_unreproducible_claims(self):
        self.assertEqual(
            classify_evidence("legacy_docx", reproducible=False, conflict=True),
            "D",
        )
        self.assertEqual(
            classify_evidence("raw_data", reproducible=True, conflict=False),
            "A",
        )
        self.assertEqual(
            classify_evidence("derived_output", reproducible=True, conflict=False),
            "B",
        )

    def test_concentration_metrics_use_all_positive_regions(self):
        metrics = concentration_metrics([50.0, 30.0, 20.0])
        self.assertEqual(metrics["cr3_pct"], 100.0)
        self.assertEqual(metrics["cr5_pct"], 100.0)
        self.assertEqual(metrics["hhi"], 3800.0)
        self.assertAlmostEqual(metrics["gini"], 0.2, places=6)

    def test_concentration_metrics_handle_zero_total(self):
        metrics = concentration_metrics([0.0, 0.0])
        self.assertEqual(metrics, {"cr3_pct": 0.0, "cr5_pct": 0.0, "hhi": 0.0, "gini": 0.0})


if __name__ == "__main__":
    unittest.main()
