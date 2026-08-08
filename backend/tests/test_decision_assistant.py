import unittest

from services.decision_assistant import build_grounding
from services.monitoring_service import build_monitoring_snapshot


class DecisionAssistantTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = build_monitoring_snapshot(
            {}, mode="demo", updated_at="2026-08-01T18:20:00+08:00"
        )

    def test_method_gap_answer_uses_snapshot_values(self):
        result = build_grounding("为什么模型比传统方法高？", self.snapshot)
        self.assertIn("18.7%", result["fallback_answer"])
        self.assertGreaterEqual(len(result["citations"]), 2)
        self.assertEqual(result["citations"][0]["data_version"], "2025.07")

    def test_risk_answer_contains_traceable_action(self):
        result = build_grounding("成都集中度风险是什么原因？", self.snapshot)
        self.assertTrue(
            any(action["type"] == "open_risk" for action in result["actions"])
        )
        self.assertNotIn("小融", result["fallback_answer"])


if __name__ == "__main__":
    unittest.main()
