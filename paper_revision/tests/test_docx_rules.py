import tempfile
import unittest
from pathlib import Path

from docx import Document

from paper_revision.build_competition_docx import (
    DESIGN,
    add_three_line_table,
    assert_no_unsupported_assertions,
)


class DocumentRuleTests(unittest.TestCase):
    def test_required_fonts_are_locked(self):
        self.assertEqual(DESIGN["east_asia_font"], "宋体")
        self.assertEqual(DESIGN["latin_font"], "Times New Roman")

    def test_three_line_table_has_no_vertical_or_inside_borders(self):
        doc = Document()
        table = add_three_line_table(doc, ["列一", "Column 2"], [["甲", "1"]])
        xml = table._tbl.xml
        self.assertIn('w:top', xml)
        self.assertIn('w:bottom', xml)
        self.assertNotIn('w:insideV', xml)
        self.assertNotIn('w:left', xml)
        self.assertNotIn('w:right', xml)

    def test_unsupported_metrics_cannot_be_written_as_results(self):
        assert_no_unsupported_assertions("未设置AUC、Kappa等监督指标，原因是缺少人工金标准。")
        with self.assertRaises(ValueError):
            assert_no_unsupported_assertions("模型结果显示AUC=0.91，Kappa=0.86。")


if __name__ == "__main__":
    unittest.main()
