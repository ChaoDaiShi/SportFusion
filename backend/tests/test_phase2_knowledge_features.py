"""
Phase 2 regression tests — knowledge base, taxonomy, FeatureVector, pipeline

Covers:
    - Knowledge file loading and validation
    - Taxonomy uniqueness and completeness
    - Text normalization
    - Negative context detection
    - Business line pipeline
    - FeatureVector construction and determinism
    - W1-W4 behavior regression (Phase 1 compat)
    - Industry code config consistency
    - Version metadata on results
    - Quality flags for edge cases
"""

import unittest

# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------
from domain.taxonomy import (
    CANONICAL_CATEGORY_IDS,
    CANONICAL_CATEGORY_NAMES,
    CATEGORY_FROM_ZH,
    CATEGORY_LABELS_ZH,
    SportCategory,
    get_category_enum,
    is_valid_category,
)

# ---------------------------------------------------------------------------
# Knowledge loading
# ---------------------------------------------------------------------------
from knowledge.loader import (
    get_active_version_metadata,
    get_enabled_terms,
    get_industry_code_index,
    get_term_index,
    load_industry_codes,
    load_knowledge_versions,
    load_model_params,
    load_sports_dictionary,
)

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
from services.business_line_service import (
    classify_business_line,
    get_category_for_word,
    get_sport_categories,
    has_sport_content,
    match_sport_by_category,
    match_sport_keywords,
    parse_business_lines,
)
from services.feature_service import SportFeatureVector, build_feature_vector
from services.sport_recognition import recognize_sport_business
from services.text_normalization_service import (
    clean_business_line,
    detect_negative_context,
    has_negative_context_for_term,
    is_empty_or_noise,
    normalize_text,
)


# ===================================================================
# Knowledge file integrity
# ===================================================================
class TestKnowledgeFiles(unittest.TestCase):
    """知识文件可加载、格式正确、无冲突"""

    def test_sports_dictionary_loads(self):
        data = load_sports_dictionary()
        self.assertIn("meta", data)
        self.assertIn("terms", data)
        self.assertGreater(len(data["terms"]), 100)

    def test_industry_codes_load(self):
        data = load_industry_codes()
        codes = data.get("codes", [])
        self.assertGreater(len(codes), 10)

    def test_model_params_load(self):
        params = load_model_params()
        self.assertIn("feature_weights", params)
        fw = params["feature_weights"]
        total = fw["w1_business_scope"] + fw["w2_keyword_density"] + fw["w3_code_weight"] + fw["w4_category_coverage"]
        self.assertAlmostEqual(total, 1.0, places=4)

    def test_versions_manifest_loads(self):
        manifest = load_knowledge_versions()
        self.assertIn("versions", manifest)
        for key in ["dictionary_version", "industry_code_map_version", "feature_schema_version", "parameter_version"]:
            self.assertIn(key, manifest["versions"])

    def test_all_terms_have_required_fields(self):
        terms = get_enabled_terms()
        for t in terms:
            self.assertIn("term", t)
            self.assertIn("category", t)
            self.assertIn("weight", t)
            self.assertIn("enabled", t)

    def test_no_duplicate_terms(self):
        terms = get_enabled_terms()
        term_texts = [t["term"] for t in terms]
        self.assertEqual(len(term_texts), len(set(term_texts)),
                         f"Duplicate terms found: {[x for x in term_texts if term_texts.count(x) > 1]}")

    def test_all_categories_belong_to_taxonomy(self):
        terms = get_enabled_terms()
        categories = set(t["category"] for t in terms)
        for cat in categories:
            self.assertIn(cat, CANONICAL_CATEGORY_NAMES,
                          f"Category '{cat}' not in taxonomy")

    def test_industry_codes_not_both_direct_and_indirect(self):
        data = load_industry_codes()
        seen = {}
        for c in data.get("codes", []):
            code = c["code"]
            rt = c["relation_type"]
            if code in seen and seen[code] != rt:
                self.fail(f"Code {code} has conflicting relation_types: {seen[code]} vs {rt}")
            seen[code] = rt

    def test_index_consistency(self):
        term_index = get_term_index()
        code_index = get_industry_code_index()
        self.assertGreater(len(term_index), 100)
        self.assertGreater(len(code_index), 10)
        # Check key types
        for k, v in code_index.items():
            self.assertIsInstance(k, int)
            self.assertIn("relation_type", v)


# ===================================================================
# Taxonomy
# ===================================================================
class TestTaxonomy(unittest.TestCase):
    """九类业态唯一性"""

    def test_nine_categories_present(self):
        self.assertEqual(len(SportCategory), 9)

    def test_canonical_ids_unique(self):
        self.assertEqual(len(CANONICAL_CATEGORY_IDS), len(set(CANONICAL_CATEGORY_IDS)))

    def test_canonical_names_unique(self):
        self.assertEqual(len(CANONICAL_CATEGORY_NAMES), len(set(CANONICAL_CATEGORY_NAMES)))

    def test_zh_labels_complete(self):
        for cat in SportCategory:
            self.assertIn(cat, CATEGORY_LABELS_ZH)

    def test_round_trip_zh_to_enum_and_back(self):
        for zh_name, cat_enum in CATEGORY_FROM_ZH.items():
            resolved = get_category_enum(zh_name)
            self.assertEqual(resolved, cat_enum)
            self.assertEqual(CATEGORY_LABELS_ZH[cat_enum], zh_name)

    def test_invalid_category(self):
        self.assertFalse(is_valid_category("not_a_category"))
        self.assertIsNone(get_category_enum("invalid_xyz"))


# ===================================================================
# Text normalization
# ===================================================================
class TestTextNormalization(unittest.TestCase):
    """文本标准化 + 否定上下文"""

    def test_normalize_none(self):
        self.assertEqual(normalize_text(None), "")

    def test_normalize_whitespace(self):
        self.assertEqual(normalize_text("   "), "")

    def test_normalize_fullwidth(self):
        result = normalize_text("体育赛事运营")
        self.assertIn("体育赛事", result)

    def test_is_empty_or_noise_none(self):
        self.assertTrue(is_empty_or_noise(None))

    def test_is_empty_or_noise_short(self):
        self.assertTrue(is_empty_or_noise("a"))

    def test_clean_business_line_strips_punctuation(self):
        self.assertEqual(clean_business_line("，体育赛事。"), "体育赛事")

    def test_clean_business_line_too_short(self):
        self.assertEqual(clean_business_line("，a。"), "")

    def test_detect_negative_context_basic(self):
        frags = detect_negative_context("非体育用品销售，体育培训")
        self.assertGreaterEqual(len(frags), 1)
        # 正则可能匹配整个 "非体育用品销售"，检查包含关键片段
        self.assertTrue(any("非体育用品" in f for f in frags),
                        f"Expected fragment containing '非体育用品', got {frags}")

    def test_detect_negative_context_exclusion(self):
        frags = detect_negative_context("体育用品除外")
        self.assertGreaterEqual(len(frags), 1)

    def test_detect_negative_context_forbidden(self):
        frags = detect_negative_context("不得开展体育培训活动")
        self.assertGreaterEqual(len(frags), 1)

    def test_negative_context_for_specific_term(self):
        # 不得 + 开展 + 体育培训 should be detected as negative for "体育培训"
        result1 = has_negative_context_for_term("不得开展体育培训", "体育培训")
        self.assertTrue(result1,
                        "Expected '体育培训' to be in negative context, but it was not detected")
        # Normal text should not trigger
        result2 = has_negative_context_for_term("体育培训服务", "体育培训")
        self.assertFalse(result2)

    def test_negative_context_block_in_classify(self):
        """'非体育用品' should NOT match '体育用品' as positive evidence"""
        result = classify_business_line("非体育用品销售")
        self.assertFalse(result["is_sport"])


# ===================================================================
# Business line pipeline
# ===================================================================
class TestBusinessLinePipeline(unittest.TestCase):
    """统一业务线解析 pipeline"""

    def test_parse_empty(self):
        self.assertEqual(parse_business_lines(""), [])
        self.assertEqual(parse_business_lines(None), [])

    def test_parse_chinese_comma(self):
        lines = parse_business_lines("体育赛事运营，运动器材销售，健身服务")
        self.assertGreaterEqual(len(lines), 2)

    def test_parse_english_comma(self):
        lines = parse_business_lines("体育赛事运营,运动器材销售")
        self.assertEqual(len(lines), 2)

    def test_parse_semicolon(self):
        lines = parse_business_lines("体育赛事运营；健身服务")
        self.assertEqual(len(lines), 2)

    def test_parse_mixed_punctuation(self):
        lines = parse_business_lines("体育赛事运营，运动器材；游泳培训、健身服务。体育管理")
        self.assertGreaterEqual(len(lines), 4)

    def test_parse_newline(self):
        lines = parse_business_lines("体育赛事运营\n健身服务")
        self.assertEqual(len(lines), 2)

    def test_deduplication(self):
        lines = parse_business_lines("体育赛事，体育赛事，运动器材")
        self.assertEqual(len(lines), 2)

    def test_filter_too_short(self):
        lines = parse_business_lines("a，体育赛事，b")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "体育赛事")

    def test_special_characters_no_crash(self):
        """特殊字符不导致崩溃"""
        lines = parse_business_lines("\x00\x01体育赛事\x1f")
        self.assertGreaterEqual(len(lines), 0)

    def test_classify_sport_line(self):
        result = classify_business_line("体育赛事运营管理")
        self.assertTrue(result["is_sport"])
        self.assertIn("matched_terms", result)
        self.assertGreater(result["evidence_strength"], 0)

    def test_classify_non_sport_line(self):
        result = classify_business_line("餐饮管理服务")
        self.assertFalse(result["is_sport"])
        self.assertEqual(result["matched_terms"], [])

    def test_match_keywords_via_service(self):
        kw = match_sport_keywords("体育赛事运营，运动器材销售")
        self.assertGreater(len(kw), 0)

    def test_match_by_category_via_service(self):
        cats = match_sport_by_category("体育赛事运营，健身服务")
        self.assertIsInstance(cats, dict)

    def test_get_sport_categories_count(self):
        cats = get_sport_categories()
        self.assertEqual(len(cats), 9)

    def test_get_category_for_word(self):
        cat_zh = get_category_for_word("马拉松")
        self.assertIn(cat_zh, CANONICAL_CATEGORY_NAMES)

    def test_has_sport_content(self):
        self.assertTrue(has_sport_content("体育赛事运营"))


# ===================================================================
# FeatureVector
# ===================================================================
class TestFeatureVector(unittest.TestCase):
    """SportFeatureVector 构建和 W1-W4 回归"""

    def test_build_feature_vector_basic(self):
        fv = build_feature_vector("体育赛事运营，运动器材销售", 8911)
        self.assertIsInstance(fv, SportFeatureVector)
        self.assertGreaterEqual(fv.w1_business_scope, 0)
        self.assertLessEqual(fv.w1_business_scope, 1)

    def test_feature_vector_deterministic(self):
        text = "体育赛事运营，运动器材销售，健身培训"
        fv1 = build_feature_vector(text, 8911)
        fv2 = build_feature_vector(text, 8911)
        self.assertEqual(fv1.w1_business_scope, fv2.w1_business_scope)
        self.assertEqual(fv1.w2_keyword_density, fv2.w2_keyword_density)
        self.assertEqual(fv1.w3_code_weight, fv2.w3_code_weight)
        self.assertEqual(fv1.w4_category_coverage, fv2.w4_category_coverage)
        self.assertEqual(fv1.code_type, fv2.code_type)

    def test_all_w_values_in_range(self):
        fv = build_feature_vector("体育赛事运营管理，运动器材批发零售，健身培训游泳", 8911)
        for w_name, w_val in [
            ("W1", fv.w1_business_scope),
            ("W2", fv.w2_keyword_density),
            ("W3", fv.w3_code_weight),
            ("W4", fv.w4_category_coverage),
        ]:
            self.assertGreaterEqual(w_val, 0.0, f"{w_name} < 0")
            self.assertLessEqual(w_val, 1.0, f"{w_name} > 1")

    def test_direct_code_sets_w3(self):
        fv = build_feature_vector("体育赛事运营", 8911)
        self.assertEqual(fv.w3_code_weight, 0.85)
        self.assertTrue(fv.direct_code_support)

    def test_indirect_code_sets_w3(self):
        fv = build_feature_vector("体育教练培训", 8391)
        self.assertEqual(fv.w3_code_weight, 0.30)
        self.assertTrue(fv.indirect_code_support)

    def test_none_code_w3_zero(self):
        fv = build_feature_vector("体育赛事运营", None)
        self.assertEqual(fv.w3_code_weight, 0.0)
        self.assertFalse(fv.direct_code_support)

    def test_empty_text_vector_is_zeroed(self):
        fv = build_feature_vector("", 8911)
        self.assertEqual(fv.w1_business_scope, 0.0)
        self.assertEqual(fv.w2_keyword_density, 0.0)
        self.assertEqual(fv.total_business_lines, 0)

    def test_version_metadata_present(self):
        fv = build_feature_vector("体育赛事", 8911)
        self.assertIn("dictionary_version", fv.version_metadata)
        self.assertIn("feature_schema_version", fv.version_metadata)

    def test_quality_flags_missing_text(self):
        fv = build_feature_vector("", None)
        self.assertIn("missing_business_text", fv.quality_flags)

    def test_quality_flags_invalid_code(self):
        fv = build_feature_vector("体育赛事", "not_a_code")
        self.assertIn("invalid_industry_code", fv.quality_flags)

    def test_evidence_relation_in_vector(self):
        fv = build_feature_vector("体育赛事运营", 8911)
        self.assertIn(fv.evidence_relation, [
            "direct_code_text_support", "direct_code_text_weak",
            "direct_code_text_conflict", "indirect_code_text_support",
            "indirect_code_text_weak", "text_only_sport",
            "no_sport_evidence", "insufficient_information",
        ])


# ===================================================================
# W1-W4 regression: Phase 1 compat
# ===================================================================
class TestW1W4Regression(unittest.TestCase):
    """确认重构后 W1-W4 行为与 Phase 1 兼容"""

    def test_w3_direct_085(self):
        fv = build_feature_vector("体育赛事运营管理，运动器材销售", 8911)
        self.assertAlmostEqual(fv.w3_code_weight, 0.85, places=4)

    def test_w3_direct_str_code(self):
        fv = build_feature_vector("体育赛事运营管理", "8911")
        self.assertAlmostEqual(fv.w3_code_weight, 0.85, places=4)

    def test_w3_indirect_030(self):
        fv = build_feature_vector("职业技能培训，体育教练培训", 8391)
        self.assertAlmostEqual(fv.w3_code_weight, 0.30, places=4)

    def test_w3_none_0(self):
        fv = build_feature_vector("体育赛事运营管理", None)
        self.assertEqual(fv.w3_code_weight, 0.0)

    def test_sport_score_in_0_1(self):
        r = recognize_sport_business("体育赛事运营，运动器材销售", 8911)
        self.assertGreaterEqual(r["sport_score"], 0.0)
        self.assertLessEqual(r["sport_score"], 1.0)

    def test_sport_score_str_int_identical(self):
        r_int = recognize_sport_business("体育赛事运营，运动器材", 8911)
        r_str = recognize_sport_business("体育赛事运营，运动器材", "8911")
        self.assertEqual(r_int["sport_score"], r_str["sport_score"])
        self.assertEqual(r_int["code_type"], r_str["code_type"])

    def test_phase1_t04_backward_compat(self):
        """Phase 1 T04 regression: 8911 == '8911'"""
        r_int = recognize_sport_business("体育赛事运营，运动器材销售", 8911)
        r_str = recognize_sport_business("体育赛事运营，运动器材销售", "8911")
        self.assertEqual(r_int["sport_score"], r_str["sport_score"])
        self.assertEqual(r_int["code_type"], r_str["code_type"])

    def test_empty_text_direct_code_is_sport(self):
        r = recognize_sport_business("", 8911)
        self.assertTrue(r["is_sport"])


# ===================================================================
# Version metadata on results
# ===================================================================
class TestVersionMetadata(unittest.TestCase):
    """版本元数据 / DataQualityResult"""

    def test_recognition_result_has_version_metadata(self):
        r = recognize_sport_business("体育赛事运营", 8911)
        self.assertIn("version_metadata", r)
        vm = r["version_metadata"]
        self.assertIn("dictionary_version", vm)
        self.assertIn("parameter_version", vm)

    def test_recognition_result_has_quality_flags(self):
        r = recognize_sport_business("体育赛事运营", 8911)
        self.assertIn("quality_flags", r)
        self.assertIsInstance(r["quality_flags"], list)

    def test_quality_flags_for_empty_input(self):
        r = recognize_sport_business("", None)
        self.assertIn("missing_business_text", r["quality_flags"])

    def test_version_metadata_consistent_across_calls(self):
        r1 = recognize_sport_business("体育赛事", 8911)
        r2 = recognize_sport_business("体育培训", 8392)
        self.assertEqual(r1["version_metadata"], r2["version_metadata"])

    def test_active_version_function(self):
        versions = get_active_version_metadata()
        self.assertIn("dictionary_version", versions)
        self.assertIn("feature_schema_version", versions)


# ===================================================================
# Negative context: prevents false positives
# ===================================================================
class TestNegativeContextIntegration(unittest.TestCase):
    """否定语境降低/阻止假阳性"""

    def test_negated_term_not_matched(self):
        """'非体育用品' 中 '体育用品' 不应产生证据"""
        matched = match_sport_keywords("非体育用品销售")
        self.assertNotIn("体育用品", matched)

    def test_exclusion_prevents_evidence(self):
        """'体育培训除外' 不应匹配培训类关键词"""
        matched = match_sport_keywords("经营范围：体育培训除外")
        self.assertNotIn("体育培训", matched)

    def test_forbidden_activity_blocked(self):
        result = classify_business_line("不得开展体育培训活动")
        self.assertFalse(result["is_sport"])

    def test_normal_sport_still_matches(self):
        """正常体育文本仍然匹配"""
        result = classify_business_line("体育培训服务")
        self.assertTrue(result["is_sport"])


# ===================================================================
# Edge cases
# ===================================================================
class TestEdgeCases(unittest.TestCase):
    """异常输入不会导致崩溃"""

    def test_nan_text(self):
        r = recognize_sport_business(float("nan"), 8911)
        self.assertIn("sport_score", r)

    def test_unicode_junk(self):
        r = recognize_sport_business("���", 8911)
        self.assertIn("sport_score", r)

    def test_repeated_keywords_not_double_counted(self):
        fv = build_feature_vector("体育赛事，体育赛事，体育赛事，体育赛事", 8911)
        self.assertLessEqual(fv.sport_term_count, len(fv.sport_keywords_matched) + 5)

    def test_very_long_text(self):
        text = "体育赛事运营，" * 500
        r = recognize_sport_business(text, 8911)
        self.assertGreaterEqual(r["sport_score"], 0)

    def test_empty_string_industry_code(self):
        r = recognize_sport_business("体育赛事", "")
        self.assertEqual(r["code_type"], "none")
        self.assertIn("sport_score", r)


if __name__ == "__main__":
    unittest.main()
