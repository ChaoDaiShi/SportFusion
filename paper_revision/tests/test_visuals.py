import json
import unittest
from pathlib import Path

from paper_revision.generate_visuals import build_figure_specs


class VisualSpecificationTest(unittest.TestCase):
    def test_specs_use_only_audited_keys_and_omit_unsupported_metrics(self):
        root = Path(__file__).resolve().parents[2]
        audit = json.loads((root / "paper_revision" / "artifacts" / "data_audit.json").read_text(encoding="utf-8"))
        specs = build_figure_specs(audit)
        filenames = {spec["file"] for spec in specs}
        self.assertIn("05_识别范围对比.png", filenames)
        self.assertIn("08_区域相对产出指数.png", filenames)
        self.assertFalse(any("ROC" in spec["title"] or "AUC" in spec["title"] for spec in specs))
        self.assertTrue(all(spec["source_keys"] for spec in specs))


if __name__ == "__main__":
    unittest.main()
