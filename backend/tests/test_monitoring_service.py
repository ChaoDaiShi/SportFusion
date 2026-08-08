import unittest

from services.monitoring_service import build_monitoring_snapshot


class MonitoringServiceTest(unittest.TestCase):
    def test_demo_snapshot_is_explicit_and_complete(self):
        snapshot = build_monitoring_snapshot(
            {}, mode="demo", updated_at="2026-08-01T18:20:00+08:00"
        )
        self.assertEqual(snapshot["provenance"]["mode"], "demo")
        self.assertTrue(snapshot["provenance"]["is_complete"])
        self.assertEqual(len(snapshot["metrics"]), 4)
        self.assertGreaterEqual(len(snapshot["risks"]), 4)
        self.assertIn("runtime_seconds_per_10k", snapshot["model_metrics"])

    def test_real_snapshot_preserves_values_without_demo_mixing(self):
        dashboard = {
            "overview": {
                "sport_enterprises": 12,
                "total_output_index": 345.6,
                "crossover_count": 4,
            },
            "map": {"data": [{"name": "成都市", "value": 210.0}]},
            "line": {
                "labels": ["2025"],
                "series": [{"name": "体育用品", "data": [210.0]}],
            },
            "concentration": {"cr3_pct": 64.0},
            "structure": {"diversity_index": 0.75},
        }
        snapshot = build_monitoring_snapshot(
            dashboard, mode="real", updated_at="2026-08-01T18:20:00+08:00"
        )
        self.assertEqual(snapshot["metrics"][0]["value"], 12)
        self.assertEqual(snapshot["metrics"][1]["value"], 345.6)
        self.assertEqual(snapshot["regions"][0]["name"], "成都市")
        self.assertEqual(snapshot["provenance"]["mode"], "real")
        self.assertFalse(snapshot["provenance"]["is_complete"])
        self.assertIn("model_metrics", snapshot["provenance"]["missing_fields"])
        self.assertEqual(snapshot["model_metrics"], {})
        self.assertEqual(snapshot["risks"][0]["type"], "industry_structure")
        self.assertNotEqual(snapshot["risks"][0]["id"], "R-2025-071")


if __name__ == "__main__":
    unittest.main()
