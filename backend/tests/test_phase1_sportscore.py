"""
Phase 1 regression tests — SportScore dual-channel + evidence_relation

Covers T01-T18 from the Phase 1 task specification.

Test methods use pure-domain assertions; they do NOT require a running
database or external API.  All tests are safe for CI (no network, no DB).
"""

import unittest

from domain.evidence_relation import (
    EvidenceRelation,
    derive_code_text_consistency,
    derive_confidence,
    derive_crossover_type,
    is_sport_candidate,
)

# ---------------------------------------------------------------------------
# Domain imports
# ---------------------------------------------------------------------------
from domain.industry_code import normalize_industry_code

# ---------------------------------------------------------------------------
# Service imports
# ---------------------------------------------------------------------------
from services.sport_recognition import (
    batch_recognize,
    batch_recognize_full,
    calculate_sport_ratio,
    classify_business_line,
    parse_business_lines,
    recognize_sport_business,
)


# ===================================================================
# T04, T08 — industry_code normalization
# ===================================================================
class TestIndustryCodeNormalization(unittest.TestCase):
    """T04: str/int 行业代码行为一致; T08: 非法代码不产生异常"""

    def test_t04_int_and_str_8911_identical(self):
        """industry_code=8911 与 '8911' 行为一致"""
        r_int = recognize_sport_business(
            business_text="体育赛事运营，运动器材销售",
            industry_code=8911,
        )
        r_str = recognize_sport_business(
            business_text="体育赛事运营，运动器材销售",
            industry_code="8911",
        )
        self.assertEqual(r_int["sport_score"], r_str["sport_score"])
        self.assertEqual(r_int["code_type"], r_str["code_type"])
        self.assertEqual(r_int["is_sport"], r_str["is_sport"])
        self.assertEqual(
            r_int["feature_weights"]["w3_code_weight"],
            r_str["feature_weights"]["w3_code_weight"],
        )

    def test_t04_str_with_spaces(self):
        """' 8911 ' 与 8911 行为一致"""
        r = recognize_sport_business(
            business_text="体育赛事运营", industry_code=" 8911 "
        )
        self.assertEqual(r["code_type"], "direct")

    def test_t04_float_8911(self):
        """8911.0 与 8911 行为一致"""
        r = recognize_sport_business(
            business_text="体育赛事运营", industry_code=8911.0
        )
        self.assertEqual(r["code_type"], "direct")

    def test_t04_str_float_8911(self):
        """'8911.0' 与 8911 行为一致"""
        r = recognize_sport_business(
            business_text="体育赛事运营", industry_code="8911.0"
        )
        self.assertEqual(r["code_type"], "direct")

    def test_t08_none_code_no_500(self):
        """None 行业代码不产生异常"""
        r = recognize_sport_business(business_text="体育赛事", industry_code=None)
        self.assertIn("sport_score", r)
        self.assertEqual(r["code_type"], "none")

    def test_t08_empty_string_no_500(self):
        """空字符串不产生异常"""
        r = recognize_sport_business(business_text="体育赛事", industry_code="")
        self.assertEqual(r["code_type"], "none")

    def test_t08_null_string_no_500(self):
        """'NULL' 不产生异常"""
        r = recognize_sport_business(business_text="体育赛事", industry_code="NULL")
        self.assertEqual(r["code_type"], "none")

    def test_t08_nan_string_no_500(self):
        """'nan' 不产生异常"""
        r = recognize_sport_business(business_text="体育赛事", industry_code="nan")
        self.assertEqual(r["code_type"], "none")

    def test_t08_invalid_string_no_500(self):
        """非法字符串不产生异常"""
        r = recognize_sport_business(
            business_text="体育赛事", industry_code="not_a_code"
        )
        self.assertEqual(r["code_type"], "none")

    def test_normalize_edge_cases(self):
        """normalize_industry_code 边界情况"""
        self.assertIsNone(normalize_industry_code(None))
        self.assertIsNone(normalize_industry_code(""))
        self.assertIsNone(normalize_industry_code("  "))
        self.assertIsNone(normalize_industry_code("NULL"))
        self.assertIsNone(normalize_industry_code("NAN"))
        self.assertIsNone(normalize_industry_code("NONE"))
        self.assertIsNone(normalize_industry_code("NA"))
        self.assertEqual(normalize_industry_code(8911), 8911)
        self.assertEqual(normalize_industry_code("8911"), 8911)
        self.assertEqual(normalize_industry_code(" 8911 "), 8911)
        self.assertEqual(normalize_industry_code(8911.0), 8911)
        self.assertEqual(normalize_industry_code("8911.0"), 8911)


# ===================================================================
# T05, T06, T07 — W3 code weights
# ===================================================================
class TestW3CodeWeights(unittest.TestCase):
    """T05: direct → 0.85; T06: indirect → 0.30; T07: none → 0"""

    def test_t05_direct_code_w3_085(self):
        """industry_code=8911 (direct) → W3 = 0.85"""
        r = recognize_sport_business(
            business_text="体育赛事运营管理，运动器材销售",
            industry_code=8911,
        )
        self.assertAlmostEqual(
            r["feature_weights"]["w3_code_weight"], 0.85, places=4
        )

    def test_t05_direct_code_str_w3_085(self):
        """industry_code='8911' (direct) → W3 = 0.85"""
        r = recognize_sport_business(
            business_text="体育赛事运营管理",
            industry_code="8911",
        )
        self.assertAlmostEqual(
            r["feature_weights"]["w3_code_weight"], 0.85, places=4
        )

    def test_t06_indirect_code_w3_030(self):
        """industry_code=8391 (indirect) → W3 = 0.30"""
        r = recognize_sport_business(
            business_text="职业技能培训，体育教练培训",
            industry_code=8391,
        )
        self.assertAlmostEqual(
            r["feature_weights"]["w3_code_weight"], 0.30, places=4
        )

    def test_t07_none_code_w3_0(self):
        """industry_code=None → W3 = 0"""
        r = recognize_sport_business(
            business_text="体育赛事运营管理",
            industry_code=None,
        )
        self.assertEqual(r["feature_weights"]["w3_code_weight"], 0.0)

    def test_t07_unknown_code_w3_0(self):
        """非体育行业代码 → W3 = 0"""
        r = recognize_sport_business(
            business_text="体育赛事运营", industry_code=9999
        )
        self.assertEqual(r["feature_weights"]["w3_code_weight"], 0.0)


# ===================================================================
# T09, T10 — empty text + code evidence
# ===================================================================
class TestEmptyTextWithCode(unittest.TestCase):
    """T09: 空文本+direct code 保留代码证据; T10: 空文本+none code 不产生证据"""

    def test_t09_empty_text_direct_code_preserves_evidence(self):
        """空文本 + direct code → is_sport=True, w3=0.85"""
        r = recognize_sport_business(business_text="", industry_code=8911)
        self.assertTrue(r["is_sport"])
        self.assertAlmostEqual(
            r["feature_weights"]["w3_code_weight"], 0.85, places=4
        )
        self.assertGreater(r["sport_score"], 0)

    def test_t10_empty_text_none_code_no_evidence(self):
        """空文本 + none code → is_sport=False, sport_score=0"""
        r = recognize_sport_business(business_text="", industry_code=None)
        self.assertFalse(r["is_sport"])
        self.assertEqual(r["sport_score"], 0.0)
        self.assertEqual(r["confidence"], 0.0)


# ===================================================================
# T11 — sport_score always in [0, 1]
# ===================================================================
class TestSportScoreBounds(unittest.TestCase):
    """T11: sport_score 始终位于 [0, 1]"""

    def test_t11_sport_score_in_bounds(self):
        """各种输入下 sport_score 都在 [0, 1]"""
        cases = [
            ("体育赛事运营，运动器材销售，健身服务", 8911),
            ("体育用品零售", 5242),
            ("餐饮服务，食品销售", None),
            ("", 8911),
            ("", None),
            ("计算机软件开发", None),
            ("体育培训，篮球教学，游泳培训，足球训练", 8392),
        ]
        for text, code in cases:
            with self.subTest(text=text[:30], code=code):
                r = recognize_sport_business(
                    business_text=text, industry_code=code
                )
                self.assertGreaterEqual(r["sport_score"], 0.0)
                self.assertLessEqual(r["sport_score"], 1.0)


# ===================================================================
# T12 — sport_score is formal domain field
# ===================================================================
class TestSportScoreField(unittest.TestCase):
    """T12: sport_score 成为正式 domain 字段"""

    def test_t12_sport_score_present(self):
        """单条识别结果包含 sport_score"""
        r = recognize_sport_business(
            business_text="体育赛事运营", industry_code=8911
        )
        self.assertIn("sport_score", r)
        self.assertIsInstance(r["sport_score"], float)

    def test_t12_batch_results_have_sport_score(self):
        """批量识别结果包含 sport_score"""
        enterprises = [
            {
                "enterprise_id": 1,
                "enterprise_name": "测试A",
                "business_text": "体育赛事运营",
                "industry_code": 8911,
            },
            {
                "enterprise_id": 2,
                "enterprise_name": "测试B",
                "business_text": "餐饮服务",
                "industry_code": None,
            },
        ]
        results = batch_recognize(enterprises)
        for r in results:
            self.assertIn("sport_score", r)

    def test_t12_batch_full_results_have_sport_score(self):
        """全量批量识别结果包含 sport_score"""
        enterprises = [
            {
                "credit_code": "X1",
                "name": "测试A",
                "business_text": "体育赛事运营",
                "industry_code": 8911,
            },
        ]
        results = batch_recognize_full(enterprises)
        for r in results:
            self.assertIn("sport_score", r)


# ===================================================================
# T13 — legacy sport_ratio does not affect candidate decision
# ===================================================================
class TestLegacySportRatio(unittest.TestCase):
    """T13: legacy sport_ratio 不影响候选判定"""

    def test_t13_legacy_ratio_equals_sport_score(self):
        """sport_ratio 等于 sport_score (identity mapping)"""
        r = recognize_sport_business(
            business_text="体育赛事运营，运动器材销售",
            industry_code=8911,
        )
        self.assertEqual(r["sport_ratio"], r["sport_score"])

    def test_t13_decision_uses_sport_score(self):
        """候选判定基于 sport_score，legacy ratio 不干扰"""
        r = recognize_sport_business(
            business_text="体育赛事运营，运动器材销售",
            industry_code=8911,
        )
        expected = r["sport_score"] >= 0.10 and bool(r["primary_sport_category"])
        expected = expected or (r["sport_score"] >= 0.05 and r["code_type"] == "direct")
        expected = expected or r["code_type"] == "direct"
        self.assertEqual(r["is_sport"], expected)


# ===================================================================
# T14, T15, T16 — evidence_relation
# ===================================================================
class TestEvidenceRelation(unittest.TestCase):
    """T14-T16: evidence_relation 对各种场景的判断"""

    def test_t14_direct_text_support(self):
        """direct code + text evidence → DIRECT_CODE_TEXT_SUPPORT"""
        r = recognize_sport_business(
            business_text="体育赛事运营，运动器材销售",
            industry_code=8911,
        )
        self.assertEqual(
            r["evidence_relation"],
            EvidenceRelation.DIRECT_CODE_TEXT_SUPPORT.value,
        )
        self.assertEqual(r["code_text_consistency"], "consistent")

    def test_t15_direct_text_conflict(self):
        """direct code + no text evidence → DIRECT_CODE_TEXT_CONFLICT"""
        r = recognize_sport_business(
            business_text="餐饮服务，食品销售",
            industry_code=8911,
        )
        self.assertEqual(
            r["evidence_relation"],
            EvidenceRelation.DIRECT_CODE_TEXT_CONFLICT.value,
        )
        self.assertEqual(r["code_text_consistency"], "conflict")

    def test_t16_text_only_sport(self):
        """none code + strong text → TEXT_ONLY_SPORT"""
        r = recognize_sport_business(
            business_text="体育赛事运营，运动器材销售，健身培训",
            industry_code=None,
        )
        self.assertTrue(r["is_sport"])
        self.assertEqual(
            r["evidence_relation"],
            EvidenceRelation.TEXT_ONLY_SPORT.value,
        )

    def test_indirect_with_text(self):
        """indirect code + text → INDIRECT_CODE_TEXT_SUPPORT"""
        r = recognize_sport_business(
            business_text="体育教练培训，篮球教学",
            industry_code=8391,
        )
        self.assertEqual(
            r["evidence_relation"],
            EvidenceRelation.INDIRECT_CODE_TEXT_SUPPORT.value,
        )

    def test_no_sport_evidence(self):
        """no code + no text → NO_SPORT_EVIDENCE"""
        r = recognize_sport_business(
            business_text="餐饮服务", industry_code=None
        )
        self.assertFalse(r["is_sport"])
        self.assertEqual(r["confidence"], 0.0)


# ===================================================================
# T01, T02, T17 — dual-channel consistency
# ===================================================================
class TestDualChannelConsistency(unittest.TestCase):
    """T01/T02: industry_code preservation; T17: single/batch/batch-full consistency"""

    def test_t01_single_passes_industry_code(self):
        """单条识别正确传递并处理 industry_code"""
        r = recognize_sport_business(
            business_text="体育赛事运营", industry_code=8911
        )
        self.assertEqual(r["code_type"], "direct")
        self.assertAlmostEqual(
            r["feature_weights"]["w3_code_weight"], 0.85, places=4
        )

    def test_t02_batch_passes_industry_code(self):
        """批量识别正确传递 industry_code"""
        enterprises = [
            {
                "enterprise_id": 1,
                "enterprise_name": "测试",
                "business_text": "体育赛事运营",
                "industry_code": 8911,
            },
        ]
        results = batch_recognize(enterprises)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["code_type"], "direct")

    def test_t17_single_batch_full_consistent(self):
        """single 和 batch_full 对同一企业结果一致"""
        text = "体育赛事运营，运动器材销售"
        code = 8911
        name = "测试体育公司"

        r_single = recognize_sport_business(
            business_text=text, industry_code=code, enterprise_name=name
        )
        r_batch = batch_recognize_full([
            {"credit_code": "T1", "name": name, "business_text": text, "industry_code": code}
        ])

        self.assertEqual(r_single["is_sport"], r_batch[0]["is_sport"])
        self.assertEqual(r_single["sport_score"], r_batch[0]["sport_score"])
        self.assertEqual(r_single["code_type"], r_batch[0]["code_type"])


# ===================================================================
# T18 — Schema
# ===================================================================
class TestSchema(unittest.TestCase):
    """T18: Schema 不再把 SportScore 描述为收入占比"""

    def test_t18_sport_score_schema_field(self):
        """sport_score schema 字段描述不含收入占比"""
        from models.schemas import RecognitionResult
        field = RecognitionResult.model_fields["sport_score"]
        desc = field.description or ""
        self.assertNotIn("营收", desc)
        self.assertNotIn("SportShare", desc)
        self.assertIn("证据", desc)

    def test_t18_sport_ratio_is_deprecated(self):
        """sport_ratio schema 字段标记 deprecated"""
        from models.schemas import RecognitionResult
        field = RecognitionResult.model_fields["sport_ratio"]
        desc = field.description or ""
        self.assertIn("deprecated", desc.lower())


# ===================================================================
# Additional: calculate_sport_ratio tests
# ===================================================================
class TestCalculateSportScore(unittest.TestCase):
    """sport_score 计算正确性"""

    def test_sport_score_range(self):
        """calculate_sport_ratio 返回值在 [0, 1]"""
        r = calculate_sport_ratio("体育赛事运营管理，运动器材销售", 8911)
        self.assertGreaterEqual(r["sport_ratio"], 0.0)
        self.assertLessEqual(r["sport_ratio"], 1.0)

    def test_empty_text_returns_zero(self):
        """空文本返回 0"""
        r = calculate_sport_ratio("", None)
        self.assertEqual(r["sport_ratio"], 0.0)

    def test_direct_code_boosts_score(self):
        """direct 代码提升 sport_score"""
        text = "体育培训"
        r_with = calculate_sport_ratio(text, 8911)
        r_without = calculate_sport_ratio(text, None)
        self.assertGreaterEqual(r_with["sport_ratio"], r_without["sport_ratio"])


# ===================================================================
# Additional: evidence_relation derive functions unit tests
# ===================================================================
class TestDeriveFunctions(unittest.TestCase):
    """evidence_relation 各派生函数的单元测试"""

    def test_derive_confidence_all_relations(self):
        """所有 relation 的 confidence 派生不崩溃"""
        for rel in EvidenceRelation:
            c = derive_confidence(rel, 0.5)
            self.assertGreaterEqual(c, 0.0)
            self.assertLessEqual(c, 1.0)

    def test_derive_code_text_consistency_all_relations(self):
        """所有 relation 的 consistency 派生有值"""
        for rel in EvidenceRelation:
            result = derive_code_text_consistency(rel)
            self.assertIn(result, ("consistent", "partial", "conflict", "unknown"))

    def test_derive_crossover_type_is_sport_false(self):
        """非体育企业不返回跨界类型"""
        ct = derive_crossover_type(
            EvidenceRelation.NO_SPORT_EVIDENCE, 0, 0, is_sport=False
        )
        self.assertEqual(ct, "")

    def test_is_sport_candidate_direct_code_always_true(self):
        """direct code → 始终是候选"""
        self.assertTrue(
            is_sport_candidate(
                sport_score=0.01,
                relation=EvidenceRelation.DIRECT_CODE_TEXT_CONFLICT,
                code_type="direct",
            )
        )

    def test_is_sport_candidate_none_code_requires_score(self):
        """none code → 需要 sport_score >= 0.10 且 primary_category"""
        self.assertFalse(
            is_sport_candidate(
                sport_score=0.05,
                relation=EvidenceRelation.INSUFFICIENT_INFORMATION,
                code_type="none",
                primary_category="",
            )
        )


# ===================================================================
# Additional: business line parsing
# ===================================================================
class TestBusinessLineParsing(unittest.TestCase):
    """业务线解析基本正确性"""

    def test_parse_simple(self):
        lines = parse_business_lines("体育赛事运营，运动器材销售")
        self.assertGreaterEqual(len(lines), 2)

    def test_parse_empty(self):
        self.assertEqual(parse_business_lines(""), [])
        self.assertEqual(parse_business_lines(None), [])

    def test_classify_sport_line(self):
        result = classify_business_line("体育赛事运营管理")
        self.assertTrue(result["is_sport"])
        self.assertGreater(len(result["keywords"]), 0)

    def test_classify_non_sport_line(self):
        result = classify_business_line("餐饮管理服务")
        self.assertFalse(result["is_sport"])
        self.assertEqual(result["keywords"], [])


if __name__ == "__main__":
    unittest.main()
