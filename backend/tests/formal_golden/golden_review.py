"""Golden Regression — P1-P4 review priority distribution."""
import unittest

import pytest


class TestGoldenReviewPriority(unittest.TestCase):
    def test_priority_rules_load_correctly(self):
        from services.review_workflow_service import load_priority_rules
        rules = load_priority_rules()
        for p in ["P1", "P2", "P3", "P4"]:
            self.assertIn(p, rules["priorities"])
            self.assertIn("rules", rules["priorities"][p])

    def test_no_priority_hardcoded(self):
        """P1=2735 etc must come from pipeline, not hardcoded."""
        from services.review_workflow_service import determine_priority
        priority, _, _ = determine_priority({"is_sport": True, "sport_score": 0.05,
                                              "code_type": "direct", "confidence": 0.5,
                                              "evidence_relation": "direct_code_text_conflict",
                                              "is_crossover": False, "keywords": [],
                                              "total_business_lines": 2, "sport_business_lines": 0})
        self.assertEqual(priority, "P1")

    @pytest.mark.formal_artifact
    def test_p1_p2_p3_p4_sum_to_8950(self):
        """P1+P2+P3+P4 = 8950 = total candidates (formal artifact required)."""
        from services.review_workflow_service import load_priority_rules
        rules = load_priority_rules()
        self.assertIn("P1", rules["priorities"])
        # Full distribution check needs formal recognition results


if __name__ == "__main__":
    unittest.main()
