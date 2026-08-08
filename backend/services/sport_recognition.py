"""
体育业务识别算法 v2.0
  - jieba 分词 + 关键词匹配（271词，9大业态）
  - 业务边界解析：拆分多条业务线，逐条分类
  - 多维度证据评分：业务范围覆盖率 + 关键词密度 + 行业代码权重 + 业态覆盖度
  - 跨界经营判定

SportScore = 体育业务证据评分 [0, 1]，不表示营收占比。
SportShare = 体育经营活动结构比重估计值，独立于 SportScore。
"""
import re
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
from utils.industry_code import (
    get_code_type,
)
from utils.industry_code import (
    get_sport_category as get_code_sport_category,
)
from utils.text_tokenizer import (
    get_category_for_word,
    get_sport_categories,
    match_sport_by_category,
    match_sport_keywords,
    tokenize,
)

# ============================================================
# 业务线解析
# ============================================================

def parse_business_lines(text: str) -> list[str]:
    """
    将「主要业务活动」文本拆分为独立的业务线
    分隔符：逗号、分号、顿号、斜杠、换行、句号等
    过滤掉过短（<2字）的业务描述
    """
    if not text:
        return []
    # 按常见业务分隔符拆分
    parts = re.split(r"[，,；;、/／\n\r。；;．\.\s]+", str(text))
    # 清理空白并过滤
    lines = [p.strip() for p in parts if len(p.strip()) >= 2]
    # 去重保持顺序
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    return unique_lines


def classify_business_line(line: str) -> dict[str, Any]:
    """
    判断单条业务线是否属于体育业务

    Returns:
        {
            "line": str,           # 原业务描述
            "is_sport": bool,      # 是否为体育业务
            "category": str,       # 体育业态分类（如果不是体育则为空）
            "keywords": [str],     # 匹配到的关键词
            "score": float,        # 匹配得分（0-1）
        }
    """
    keywords = match_sport_keywords(line)
    if not keywords:
        return {"line": line, "is_sport": False, "category": "", "keywords": [], "score": 0.0}

    # 按类别统计命中
    categories = match_sport_by_category(line)
    # 选择命中关键词最多的类别（处理空字典情况）
    if not categories:
        best_cat = ""
    else:
        best_cat = max(categories, key=lambda c: len(categories[c]))
    score = min(len(keywords) / 3.0, 1.0)  # 命中3个以上即为满分

    return {
        "line": line,
        "is_sport": True,
        "category": best_cat,
        "keywords": keywords,
        "score": round(score, 2),
    }


# ============================================================
# 比重测算模型
# ============================================================

def calculate_sport_ratio(
    text: str,
    industry_code: int | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """
    多维度特征加权评分，量化企业体育业务在整体经营中的占比

    四个维度：
      W1=0.40  业务范围占比 (sport_lines / total_lines)
      W2=0.25  关键词密度    (sport_hits / total_tokens)
      W3=0.25  行业代码权重  (code_type_weight)
      W4=0.10  业态覆盖度    (sport_category_count / total_categories)

    Returns:
        { sport_ratio, business_lines, sport_lines, details }
    """
    if not text:
        return _empty_ratio_result()

    # Normalize industry code to int|None for consistent handling
    norm_code = normalize_industry_code(industry_code)

    # --- W1: 业务范围占比 ---
    business_lines = parse_business_lines(text)
    total_lines = len(business_lines)
    classified = [classify_business_line(line) for line in business_lines]
    sport_lines = [c for c in classified if c["is_sport"]]
    sport_line_count = len(sport_lines)
    w1 = sport_line_count / total_lines if total_lines > 0 else 0.0

    # --- W2: 关键词密度 ---
    all_sport_keywords = match_sport_keywords(text)
    tokens = tokenize(text)
    token_count = len(tokens) if tokens else 1
    sport_hit_count = len(all_sport_keywords)
    w2 = min(sport_hit_count / token_count * 10, 1.0)  # 归一化

    # --- W3: 行业代码权重 ---
    if norm_code is not None:
        code_type = get_code_type(norm_code)
        if code_type == "direct":
            w3 = 0.85
        elif code_type == "indirect":
            w3 = 0.30
        else:
            w3 = 0.0  # 非体育代码不给权重
    else:
        w3 = 0.0

    # --- W4: 业态覆盖度 ---
    sport_categories_all = set()
    for kw in all_sport_keywords:
        cat = get_category_for_word(kw)
        if cat:
            sport_categories_all.add(cat)
    all_categories = get_sport_categories()
    w4 = len(sport_categories_all) / len(all_categories) if all_categories else 0.0

    # --- 加权综合 ---
    ratio = round(0.40 * w1 + 0.25 * w2 + 0.25 * w3 + 0.10 * w4, 4)
    ratio = min(ratio, 1.0)  # 上限 100%

    # 确定主要体育业态
    category_counts: dict[str, int] = {}
    for sl in sport_lines:
        cat = sl["category"]
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1
    primary_category = max(category_counts, key=category_counts.get) if category_counts else ""

    return {
        "sport_ratio": ratio,
        "total_business_lines": total_lines,
        "sport_business_lines": sport_line_count,
        "business_lines": [c["line"] for c in classified],
        "sport_lines_detail": sport_lines,
        "non_sport_lines": [c["line"] for c in classified if not c["is_sport"]],
        "sport_keywords_matched": all_sport_keywords,
        "sport_category_count": len(sport_categories_all),
        "primary_sport_category": primary_category,
        "all_sport_categories": list(sport_categories_all),
        "feature_weights": {
            "w1_business_scope": round(w1, 4),
            "w2_keyword_density": round(w2, 4),
            "w3_code_weight": round(w3, 4),
            "w4_category_coverage": round(w4, 4),
        },
        "total_tokens": token_count,
        "sport_hit_count": sport_hit_count,
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
        "feature_weights": {"w1_business_scope": 0, "w2_keyword_density": 0, "w3_code_weight": 0, "w4_category_coverage": 0},
        "total_tokens": 0,
        "sport_hit_count": 0,
    }


def _determine_code_text_consistency(
    code_type: str,
    is_sport: bool,
    sport_ratio: float,
    keywords: list[str],
) -> str:
    """
    判定行业代码与业务文本描述的一致性

    返回:
      - consistent:   代码类型与文本匹配（direct+有命中 | none+无命中）
      - partial:      部分匹配（indirect+有少量命中）
      - conflict:     冲突（direct+无命中 或 none+高命中）
      - unknown:      无法判断（文本为空或无代码）
    """
    has_text_evidence = len(keywords) > 0

    if code_type == "direct" and has_text_evidence:
        return "consistent"
    elif code_type == "direct" and not has_text_evidence:
        return "conflict"  # 代码说是体育但文本找不到证据
    elif code_type == "indirect" and has_text_evidence:
        return "partial"  # 间接代码+文本有体育=部分匹配
    elif code_type == "none" and has_text_evidence and sport_ratio > 0.3:
        return "conflict"  # 非体育代码但文本强体育信号
    elif code_type == "none" and not has_text_evidence:
        return "consistent"  # 代码和文本都非体育
    elif code_type == "none" and has_text_evidence and sport_ratio < 0.3:
        return "partial"
    elif not code_type or code_type == "none":
        return "unknown"
    return "unknown"


# ============================================================
# 综合识别（保持向后兼容的 API）
# ============================================================

def recognize_sport_business(
    business_text: str,
    industry_code: int | None = None,
    enterprise_name: str | None = None,
) -> dict:
    """
    综合识别：企业体育业态分类 + 业务边界 + 比重测算

    Returns:
        {
            sport_category, is_sport, sport_ratio, confidence,
            business_lines, sport_lines, crossover_type,
            keywords, ...
        }
    """
    # Normalize industry code to int|None for consistent handling
    norm_code = normalize_industry_code(industry_code)

    if not business_text:
        # 空文本时，直接体育代码仍判定为体育（代码是最强先验信号）
        code_type = get_code_type(norm_code) if norm_code else "none"
        if code_type == "direct":
            code_cat = get_code_sport_category(norm_code) or ""
            return {
                "sport_category": code_cat,
                "is_sport": True,
                "sport_score": 0.2125,  # 0.25*0.85 = 仅代码权重
                "sport_ratio": 0.2125,   # deprecated：保留兼容
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
                "feature_weights": {"w1_business_scope": 0.0, "w2_keyword_density": 0.0, "w3_code_weight": 0.85, "w4_category_coverage": 0.0},
                "primary_sport_category": code_cat,
                "all_sport_categories": [],
            }
        return {
            "sport_category": "非体育",
            "is_sport": False,
            "sport_score": 0.0,
            "sport_ratio": 0.0,  # deprecated：保留兼容
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
            "feature_weights": {"w1_business_scope": 0.0, "w2_keyword_density": 0.0, "w3_code_weight": 0.0, "w4_category_coverage": 0.0},
            "primary_sport_category": "",
            "all_sport_categories": [],
        }

    # 证据评分测算（包含业务边界解析）
    ratio_result = calculate_sport_ratio(business_text, norm_code, enterprise_name)

    # 融合行业代码信息判断最终分类 — 使用统一 evidence_relation
    code_type = get_code_type(norm_code) if norm_code else "none"
    sport_score = ratio_result["sport_ratio"]
    primary_category = ratio_result["primary_sport_category"]

    # ---- 统一证据关系 ----
    keywords = ratio_result["sport_keywords_matched"]
    text_evidence = len(keywords) > 0
    relation = derive_evidence_relation(
        code_type=code_type,
        text_evidence=text_evidence,
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

    # 确定最终业态分类
    if is_sport:
        if primary_category:
            sport_category = primary_category
        elif code_type == "direct":
            sport_category = get_code_sport_category(norm_code) or ""
        else:
            sport_category = ""
    else:
        sport_category = "非体育"

    # ---- 从 evidence_relation 派生所有下游字段 ----
    confidence = derive_confidence(relation, sport_score)
    code_text_consistency = derive_code_text_consistency(relation)
    crossover_type = derive_crossover_type(
        relation=relation,
        sport_lines_count=ratio_result["sport_business_lines"],
        total_lines=ratio_result["total_business_lines"],
        is_sport=is_sport,
    )
    is_crossover = bool(crossover_type)

    # ---- 保留旧 consistency 函数为兼容 fallback ----
    # 当 relation 返回 unknown 时回退到旧逻辑
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
        "sport_score": sport_score,     # 正式字段：体育业务证据评分
        "sport_ratio": sport_score,      # deprecated：保留兼容旧接口
        "confidence": round(confidence, 2),
        "is_crossover": is_crossover,
        "crossover_type": crossover_type,
        "code_type": code_type,
        "code_text_consistency": code_text_consistency,
        "evidence_relation": relation.value,
        "total_business_lines": ratio_result["total_business_lines"],
        "sport_business_lines": ratio_result["sport_business_lines"],
        "business_lines": ratio_result["business_lines"],
        "sport_lines": ratio_result["sport_lines_detail"],
        "non_sport_lines": ratio_result["non_sport_lines"],
        "keywords": ratio_result["sport_keywords_matched"],
        "feature_weights": ratio_result["feature_weights"],
        "primary_sport_category": primary_category,
        "all_sport_categories": ratio_result["all_sport_categories"],
    }


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
    """
    全量批量识别（包含完整业务边界+比重信息）

    enterprises: [{"credit_code", "name", "industry_code", "business_text"}, ...]
    """
    results = []
    for ent in enterprises:
        result = recognize_sport_business(
            business_text=ent.get("business_text", ""),
            industry_code=ent.get("industry_code"),
            enterprise_name=ent.get("name", ""),
        )
        # 携带原始标识
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

    # 类别分布
    cat_dist: dict[str, int] = {}
    for r in results:
        cat = r.get("sport_category", "非体育")
        cat_dist[cat] = cat_dist.get(cat, 0) + 1

    # SportScore 区间分布
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

    # 跨界类型分布
    crossover_types: dict[str, int] = {}
    for r in results:
        ct = r.get("crossover_type", "")
        if ct:
            crossover_types[ct] = crossover_types.get(ct, 0) + 1

    # 平均 SportScore
    sport_scores = [r.get("sport_score", r.get("sport_ratio", 0)) for r in results if r.get("is_sport")]
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
        "avg_sport_ratio": round(avg_score, 4),  # deprecated: legacy compat
        "avg_sport_ratio_pct": round(avg_score * 100, 2),  # deprecated: legacy compat
    }
