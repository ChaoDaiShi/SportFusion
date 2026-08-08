import unittest

from paper_revision.extract_docx_claims import extract_numeric_tokens, risk_tags


class ClaimExtractionTest(unittest.TestCase):
    def test_extracts_counts_rates_and_named_metrics(self):
        text = "样本量n=300，AUC=0.91，识别覆盖率由10.45%升至11.67%，新增934家。"
        tokens = extract_numeric_tokens(text)
        self.assertIn("300", tokens)
        self.assertIn("0.91", tokens)
        self.assertIn("10.45%", tokens)
        self.assertIn("11.67%", tokens)
        self.assertIn("934", tokens)

    def test_flags_unsupported_evaluation_and_prediction_claims(self):
        tags = risk_tags("预计2028年产值增长，AUC达到0.91，可节省成本300万元。")
        self.assertIn("evaluation", tags)
        self.assertIn("forecast", tags)
        self.assertIn("economic_benefit", tags)


if __name__ == "__main__":
    unittest.main()
