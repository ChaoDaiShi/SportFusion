"""
体育业务识别算法 v2.1
  - 知识库驱动的关键词匹配（271词，9大业态）
  - 业务边界解析：拆分多条业务线，逐条分类
  - 统一特征向量 SportFeatureVector
  - 跨界经营判定

SportScore = 体育业务证据评分 [0, 1]，不表示营收占比。
SportShare = 体育经营活动结构比重估计值，独立于 SportScore。

Phase 2: 所有特征计算委托给 feature_service.build_feature_vector()。
         识别模块只消费标准化证据，不自行解析文本或行业代码。
"""
from typing import Any

from domain.evidence_relation import (
    EvidenceRelation,
    derive_code_text_consistency,
    derive_confidence,
    derive_crossover_type,
    derive_evidence_relation,
    is_sport_candidate,
)
from domain.industry_code import normalize_industry_code
from knowledge.loader import get_feature_weights
from utils.industry_code import (
    get_code_type,
)
from utils.industry_code import (
    get_sport_category as get_code_sport_category,
)

from services.business_line_service import (
    classify_business_line as _classify_business_line,
)
from services.business_line_service import (
    parse_business_lines as _parse_business_lines,
)
from services.feature_service import build_feature_vector

# ============================================================
# 业务线解析 (thin wrappers — delegate to business_line_service)
# ============================================================

parse_business_lines = _parse_business_lines
classify_business_line = _classify_business_line


# ============================================================
# 特征评分计算 (delegates to build_feature_vector)
# ============================================================

def calculate_sport_ratio(
    text: str,
    industry_code: int | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """
    【deprecated】多维度特征加权评分。

    Phase 2: 此函数保留为兼容 wrapper，实际计算委托给 build_feature_vector()。
    新代码应直接使用 feature_service.build_feature_vector()。
    """
    fv = build_feature_vector(
        business_text=text,
        industry_code=industry_code,
        enterprise_name=name,
    )

    weights = get_feature_weights()
    w1 = fv.w1_business_scope
    w2 = fv.w2_keyword_density
    w3 = fv.w3_code_weight
    w4 = fv.w4_category_coverage

    ratio = round(
        weights["w1_business_scope"] * w1
        + weights["w2_keyword_density"] * w2
        + weights["w3_code_weight"] * w3
        + weights["w4_category_coverage"] * w4,
        4,
    )
    ratio = min(ratio, 1.0)

    return {
        "sport_ratio": ratio,
        "total_business_lines": fv.total_business_lines,
        "sport_business_lines": fv.sport_business_lines,
        "business_lines": fv.business_lines,
        "sport_lines_detail": fv.sport_lines_detail,
        "non_sport_lines": fv.non_sport_lines,
        "sport_keywords_matched": fv.sport_keywords_matched,
        "sport_category_count": fv.category_count,
        "primary_sport_category": fv.primary_sport_category,
        "all_sport_categories": fv.all_sport_categories,
        "feature_weights": {
            "w1_business_scope": round(w1, 4),
            "w2_keyword_density": round(w2, 4),
            "w3_code_weight": round(w3, 4),
            "w4_category_coverage": round(w4, 4),
        },
        "total_tokens": fv.token_count,
        "sport_hit_count": fv.sport_term_count,
    }


def _empty_ratio_result() -> dict[str, Any]:
    return {
        "sport_ratio": 0.0,
        "total_business_lines": 0,
        "sport_business_lines": 0,
        "business_lines": [],
        "sport_lines_detail": [],
        "non_sport_lines": [],
        "sport_keywords_matched": [],
        "sport_category_count": 0,
        "primary_sport_category": "",
        "all_sport_categories": [],
        "feature_weights": {
            "w1_business_scope": 0, "w2_keyword_density": 0,
            "w3_code_weight": 0, "w4_category_coverage": 0,
        },
        "total_tokens": 0,
        "sport_hit_count": 0,
    }


# ============================================================
# 兼容性保留函数
# ============================================================

def _determine_code_text_consistency(
    code_type: str,
    is_sport: bool,
    sport_ratio: float,
    keywords: list[str],
) -> str:
    """[deprecated] 旧 consistency fallback — 保留用于未知 relation 回退"""
    has_text_evidence = len(keywords) > 0
    if code_type == "direct" and has_text_evidence:
        return "consistent"
    elif code_type == "direct" and not has_text_evidence:
        return "conflict"
    elif code_type == "indirect" and has_text_evidence:
        return "partial"
    elif code_type == "none" and has_text_evidence and sport_ratio > 0.3:
        return "conflict"
    elif code_type == "none" and not has_text_evidence:
        return "consistent"
    elif code_type == "none" and has_text_evidence and sport_ratio < 0.3:
        return "partial"
    elif not code_type or code_type == "none":
        return "unknown"
    return "unknown"


# ============================================================
# 综合识别 — 消费 SportFeatureVector
# ============================================================

def recognize_sport_business(
    business_text: str,
    industry_code: int | None = None,
    enterprise_name: str | None = None,
) -> dict:
    """
    综合识别：企业体育业态分类 + 业务边界 + 证据评分。

    Phase 2: 全部特征来自 build_feature_vector()，
    识别逻辑只做分类/判定/派生，不再自行解析文本。
    """
    norm_code = normalize_industry_code(industry_code)
    fv = build_feature_vector(
        business_text=business_text,
        industry_code=industry_code,
        enterprise_name=enterprise_name,
    )

    # 空文本 + direct code 特殊路径
    if not business_text:
        code_type = get_code_type(norm_code) if norm_code else "none"
        if code_type == "direct":
            code_cat = get_code_sport_category(norm_code) or ""
            return {
                "sport_category": code_cat,
                "is_sport": True,
                "sport_score": 0.2125,
                "sport_ratio": 0.2125,
                "confidence": 0.85,
                "is_crossover": False,
                "crossover_type": "",
                "code_type": code_type,
                "code_text_consistency": "partial",
                "evidence_relation": EvidenceRelation.DIRECT_CODE_TEXT_CONFLICT.value,
                "total_business_lines": 0,
                "sport_business_lines": 0,
                "business_lines": [],
                "sport_lines": [],
                "non_sport_lines": [],
                "keywords": [],
                "feature_weights": {
                    "w1_business_scope": 0.0, "w2_keyword_density": 0.0,
                    "w3_code_weight": 0.85, "w4_category_coverage": 0.0,
                },
                "primary_sport_category": code_cat,
                "all_sport_categories": [],
                "version_metadata": fv.version_metadata,
                "quality_flags": fv.quality_flags,
            }
        return {
            "sport_category": "非体育",
            "is_sport": False,
            "sport_score": 0.0,
            "sport_ratio": 0.0,
            "confidence": 0.0,
            "is_crossover": False,
            "crossover_type": "",
            "code_type": code_type,
            "code_text_consistency": "consistent" if code_type == "none" else "unknown",
            "evidence_relation": EvidenceRelation.NO_SPORT_EVIDENCE.value,
            "total_business_lines": 0,
            "sport_business_lines": 0,
            "business_lines": [],
            "sport_lines": [],
            "non_sport_lines": [],
            "keywords": [],
            "feature_weights": {
                "w1_business_scope": 0.0, "w2_keyword_density": 0.0,
                "w3_code_weight": 0.0, "w4_category_coverage": 0.0,
            },
            "primary_sport_category": "",
            "all_sport_categories": [],
            "version_metadata": fv.version_metadata,
            "quality_flags": fv.quality_flags,
        }

    # ---- 从 FeatureVector 提取所有字段 ----
    code_type = fv.code_type
    weights = get_feature_weights()
    sport_score = round(
        weights["w1_business_scope"] * fv.w1_business_scope
        + weights["w2_keyword_density"] * fv.w2_keyword_density
        + weights["w3_code_weight"] * fv.w3_code_weight
        + weights["w4_category_coverage"] * fv.w4_category_coverage,
        4,
    )
    sport_score = min(sport_score, 1.0)

    primary_category = fv.primary_sport_category
    keywords = fv.sport_keywords_matched

    # ---- 统一证据关系 ----
    relation = derive_evidence_relation(
        code_type=code_type,
        text_evidence=len(keywords) > 0,
        sport_score=sport_score,
        keyword_count=len(keywords),
    )

    # ---- 统一候选判定 ----
    is_sport = is_sport_candidate(
        sport_score=sport_score,
        relation=relation,
        code_type=code_type,
        primary_category=primary_category,
    )

    # ---- 业态分类 ----
    if is_sport:
        if primary_category:
            sport_category = primary_category
        elif code_type == "direct":
            sport_category = get_code_sport_category(norm_code) or ""
        else:
            sport_category = ""
    else:
        sport_category = "非体育"

    # ---- 派生字段 ----
    confidence = derive_confidence(relation, sport_score)
    code_text_consistency = derive_code_text_consistency(relation)
    crossover_type = derive_crossover_type(
        relation=relation,
        sport_lines_count=fv.sport_business_lines,
        total_lines=fv.total_business_lines,
        is_sport=is_sport,
    )
    is_crossover = bool(crossover_type)

    if code_text_consistency == "unknown":
        code_text_consistency = _determine_code_text_consistency(
            code_type=code_type,
            is_sport=is_sport,
            sport_ratio=sport_score,
            keywords=keywords,
        )

    return {
        "sport_category": sport_category,
        "is_sport": is_sport,
        "sport_score": sport_score,
        "sport_ratio": sport_score,
        "confidence": round(confidence, 2),
        "is_crossover": is_crossover,
        "crossover_type": crossover_type,
        "code_type": code_type,
        "code_text_consistency": code_text_consistency,
        "evidence_relation": relation.value,
        "total_business_lines": fv.total_business_lines,
        "sport_business_lines": fv.sport_business_lines,
        "business_lines": fv.business_lines,
        "sport_lines": fv.sport_lines_detail,
        "non_sport_lines": fv.non_sport_lines,
        "keywords": keywords,
        "feature_weights": {
            "w1_business_scope": round(fv.w1_business_scope, 4),
            "w2_keyword_density": round(fv.w2_keyword_density, 4),
            "w3_code_weight": round(fv.w3_code_weight, 4),
            "w4_category_coverage": round(fv.w4_category_coverage, 4),
        },
        "primary_sport_category": primary_category,
        "all_sport_categories": fv.all_sport_categories,
        "version_metadata": fv.version_metadata,
        "quality_flags": fv.quality_flags,
    }


# ============================================================
# 批量识别 (unchanged wrappers)
# ============================================================

def batch_recognize(enterprises: list) -> list:
    """批量企业体育业态识别（保持兼容）"""
    results = []
    for ent in enterprises:
        result = recognize_sport_business(
            business_text=ent.get("business_text", ""),
            industry_code=ent.get("industry_code"),
            enterprise_name=ent.get("enterprise_name", ""),
        )
        result["enterprise_id"] = ent.get("enterprise_id")
        result["enterprise_name"] = ent.get("enterprise_name", "")
        result["_uid"] = ent.get("_uid")
        results.append(result)
    return results


def batch_recognize_full(enterprises: list[dict]) -> list[dict]:
    """全量批量识别（包含完整业务边界+比重信息）"""
    results = []
    for ent in enterprises:
        result = recognize_sport_business(
            business_text=ent.get("business_text", ""),
            industry_code=ent.get("industry_code"),
            enterprise_name=ent.get("name", ""),
        )
        result["credit_code"] = ent.get("credit_code", "")
        result["enterprise_name"] = ent.get("name", ent.get("enterprise_name", ""))
        result["industry_code"] = ent.get("industry_code")
        results.append(result)
    return results


def get_recognition_stats(results: list[dict]) -> dict:
    """识别结果统计"""
    total = len(results)
    sport_count = sum(1 for r in results if r.get("is_sport"))
    crossover_count = sum(1 for r in results if r.get("is_crossover"))

    cat_dist: dict[str, int] = {}
    for r in results:
        cat = r.get("sport_category", "非体育")
        cat_dist[cat] = cat_dist.get(cat, 0) + 1

    ratio_bins = {"0": 0, "0-0.2": 0, "0.2-0.5": 0, "0.5-0.8": 0, "0.8-1.0": 0}
    for r in results:
        ratio = r.get("sport_score", r.get("sport_ratio", 0))
        if ratio == 0:
            ratio_bins["0"] += 1
        elif ratio <= 0.2:
            ratio_bins["0-0.2"] += 1
        elif ratio <= 0.5:
            ratio_bins["0.2-0.5"] += 1
        elif ratio <= 0.8:
            ratio_bins["0.5-0.8"] += 1
        else:
            ratio_bins["0.8-1.0"] += 1

    crossover_types: dict[str, int] = {}
    for r in results:
        ct = r.get("crossover_type", "")
        if ct:
            crossover_types[ct] = crossover_types.get(ct, 0) + 1

    sport_scores = [
        r.get("sport_score", r.get("sport_ratio", 0))
        for r in results if r.get("is_sport")
    ]
    avg_score = sum(sport_scores) / len(sport_scores) if sport_scores else 0.0

    return {
        "total": total,
        "sport_count": sport_count,
        "sport_ratio_pct": round(sport_count / total * 100, 2) if total > 0 else 0,
        "crossover_count": crossover_count,
        "crossover_pct": round(crossover_count / total * 100, 2) if total > 0 else 0,
        "category_distribution": cat_dist,
        "ratio_distribution": ratio_bins,
        "crossover_types": crossover_types,
        "avg_sport_score": round(avg_score, 4),
        "avg_sport_score_pct": round(avg_score * 100, 2),
        "avg_sport_ratio": round(avg_score, 4),
        "avg_sport_ratio_pct": round(avg_score * 100, 2),
    }
