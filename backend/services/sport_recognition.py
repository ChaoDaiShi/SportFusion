"""
体育业务识别算法 v2.0
  - jieba 分词 + 关键词匹配（271词，9大业态）
  - 业务边界解析：拆分多条业务线，逐条分类
  - 多维度比重测算：业务范围占比 + 关键词密度 + 行业代码权重 + 业态覆盖度
  - 跨界经营判定
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from utils.text_tokenizer import (
    tokenize, match_sport_keywords, match_sport_by_category,
    get_sport_categories, get_category_for_word,
)
from utils.industry_code import (
    get_code_type, get_sport_category as get_code_sport_category,
    is_direct_sport_code,
)

# ============================================================
# 业务线解析
# ============================================================

def parse_business_lines(text: str) -> List[str]:
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


def classify_business_line(line: str) -> Dict[str, Any]:
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
    industry_code: Optional[int] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
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
    if industry_code is not None:
        code_type = get_code_type(industry_code)
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
    category_counts: Dict[str, int] = {}
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


def _empty_ratio_result() -> Dict[str, Any]:
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
    keywords: List[str],
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
    industry_code: Optional[int] = None,
    enterprise_name: Optional[str] = None,
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
    if not business_text:
        # 空文本时，直接体育代码仍判定为体育（代码是最强先验信号）
        code_type = get_code_type(industry_code) if industry_code else "none"
        if code_type == "direct":
            code_cat = get_code_sport_category(industry_code) or ""
            return {
                "sport_category": code_cat,
                "is_sport": True,
                "sport_ratio": 0.2125,  # 0.25*0.85 = 仅代码权重
                "confidence": 0.85,
                "is_crossover": False,
                "crossover_type": "",
                "code_type": code_type,
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
            "sport_ratio": 0.0,
            "confidence": 0.0,
            "is_crossover": False,
            "crossover_type": "",
            "code_type": code_type,
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

    # 比重测算（包含业务边界解析）
    ratio_result = calculate_sport_ratio(business_text, industry_code, enterprise_name)

    # 融合行业代码信息判断最终分类
    code_type = get_code_type(industry_code) if industry_code else "none"
    sport_ratio = ratio_result["sport_ratio"]
    primary_category = ratio_result["primary_sport_category"]

    # 确定最终分类
    # 阈值: 体育占比 >= 10% 或行业代码是直接体育代码
    if sport_ratio >= 0.10 and primary_category:
        sport_category = primary_category
        is_sport = True
    elif sport_ratio >= 0.05 and code_type == "direct":
        sport_category = get_code_sport_category(industry_code) or primary_category or ""
        is_sport = True
    elif code_type == "direct":
        # 直接体育代码，即使文本不匹配也标记（纯代码驱动）
        sport_category = get_code_sport_category(industry_code) or ""
        is_sport = True
    else:
        sport_category = "非体育"
        is_sport = False

    # 置信度
    if code_type == "direct" and sport_ratio >= 0.3:
        confidence = 0.95
    elif code_type == "direct" and sport_ratio >= 0.1:
        confidence = 0.85
    elif sport_ratio >= 0.5:
        confidence = 0.90
    elif sport_ratio >= 0.2:
        confidence = 0.75
    elif sport_ratio >= 0.1:
        confidence = 0.60
    elif code_type == "direct":
        confidence = 0.55  # 直接代码，文本无匹配
    else:
        confidence = 0.0

    # 跨界判定
    is_crossover = False
    crossover_type = ""
    if is_sport and code_type == "none":
        is_crossover = True
        crossover_type = "纯跨界（行业代码非体育，文本有体育业务）"
    elif is_sport and code_type == "indirect":
        is_crossover = True
        crossover_type = "潜在跨界（间接行业代码，文本有体育业务）"
    elif is_sport and code_type == "direct" and ratio_result["total_business_lines"] > 1:
        # 直接体育代码但有多个业务线，可能存在非体育业务
        non_sport_count = ratio_result["total_business_lines"] - ratio_result["sport_business_lines"]
        if non_sport_count > 0:
            is_crossover = True
            crossover_type = f"多元经营（体育+{non_sport_count}条非体育业务）"

    # 代码-文本一致性判定
    code_text_consistency = _determine_code_text_consistency(
        code_type=code_type,
        is_sport=is_sport,
        sport_ratio=sport_ratio,
        keywords=ratio_result["sport_keywords_matched"],
    )

    return {
        "sport_category": sport_category,
        "is_sport": is_sport,
        "sport_ratio": sport_ratio,
        "confidence": round(confidence, 2),
        "is_crossover": is_crossover,
        "crossover_type": crossover_type,
        "code_type": code_type,
        "code_text_consistency": code_text_consistency,
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


def batch_recognize_full(enterprises: List[Dict]) -> List[Dict]:
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


def get_recognition_stats(results: List[Dict]) -> Dict:
    """识别结果统计"""
    total = len(results)
    sport_count = sum(1 for r in results if r.get("is_sport"))
    crossover_count = sum(1 for r in results if r.get("is_crossover"))

    # 类别分布
    cat_dist: Dict[str, int] = {}
    for r in results:
        cat = r.get("sport_category", "非体育")
        cat_dist[cat] = cat_dist.get(cat, 0) + 1

    # 比重区间分布
    ratio_bins = {"0": 0, "0-0.2": 0, "0.2-0.5": 0, "0.5-0.8": 0, "0.8-1.0": 0}
    for r in results:
        ratio = r.get("sport_ratio", 0)
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
    crossover_types: Dict[str, int] = {}
    for r in results:
        ct = r.get("crossover_type", "")
        if ct:
            crossover_types[ct] = crossover_types.get(ct, 0) + 1

    # 平均比重
    sport_ratios = [r.get("sport_ratio", 0) for r in results if r.get("is_sport")]
    avg_ratio = sum(sport_ratios) / len(sport_ratios) if sport_ratios else 0.0

    return {
        "total": total,
        "sport_count": sport_count,
        "sport_ratio_pct": round(sport_count / total * 100, 2) if total > 0 else 0,
        "crossover_count": crossover_count,
        "crossover_pct": round(crossover_count / total * 100, 2) if total > 0 else 0,
        "category_distribution": cat_dist,
        "ratio_distribution": ratio_bins,
        "crossover_types": crossover_types,
        "avg_sport_ratio": round(avg_ratio, 4),
        "avg_sport_ratio_pct": round(avg_ratio * 100, 2),
    }
