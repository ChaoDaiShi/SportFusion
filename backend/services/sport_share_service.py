"""
SportShare 体育经营活动比重测算服务 v1.0

在 W1-W4 规则加权模型基础上，增加：
  - 比重档位映射（5档）
  - 置信区间估计
  - 主要影响因素生成
  - 人工校准支持

核心公式：SportShare = f(W1, W2, W3, W4, 业务线特征, 置信度)
"""

import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


# ============================================================
# 比重档位定义
# ============================================================

SHARE_BANDS = {
    "very_low":  {"range": (0.0, 0.10),  "label": "极低比重",   "color": "#909399", "description": "几乎不涉及体育业务"},
    "low":       {"range": (0.10, 0.30), "label": "低比重",     "color": "#e6a23c", "description": "少量涉足体育"},
    "medium":    {"range": (0.30, 0.50), "label": "中等比重",   "color": "#f56c6c", "description": "体育为辅助业务"},
    "medium_high": {"range": (0.50, 0.75), "label": "中高比重", "color": "#409eff", "description": "体育为主要业务之一"},
    "high":      {"range": (0.75, 1.01), "label": "高比重",    "color": "#67c23a", "description": "以体育为核心业务"},
}


def get_share_band(share: float) -> Dict[str, str]:
    """根据比重值确定档位"""
    for band_key, band_info in SHARE_BANDS.items():
        low, high = band_info["range"]
        if low <= share < high:
            return {"key": band_key, **band_info}
    return {"key": "medium", **SHARE_BANDS["medium"]}


# ============================================================
# 预测区间计算
# ============================================================

def calculate_confidence_interval(
    share: float,
    confidence: float,
    sport_lines_count: int,
    total_lines: int,
    code_type: str = "none",
) -> Tuple[float, float]:
    """
    基于现有信息估计比重预测区间

    区间宽度取决于：
      - 置信度（越高越窄）
      - 业务线占比（用于W1的信息量）
      - 行业代码类型（direct更可靠）

    Returns: (lower_bound, upper_bound)
    """
    # 基础不确定度：与置信度负相关
    base_uncertainty = (1.0 - confidence) * 0.25

    # 业务线数量影响（业务线越多，估计越不确定）
    if total_lines > 0:
        lines_factor = 1.0 / math.sqrt(total_lines)
    else:
        lines_factor = 0.5  # 无业务线信息时不确定性大

    # 代码类型影响
    code_factors = {"direct": 0.6, "indirect": 0.85, "none": 1.0}
    code_factor = code_factors.get(code_type, 1.0)

    # 综合区间半宽
    half_width = base_uncertainty * lines_factor * code_factor

    # 确保区间在 [0, 1] 内
    lower = max(0.0, share - half_width)
    upper = min(1.0, share + half_width)

    return round(lower, 4), round(upper, 4)


# ============================================================
# 主要影响因素生成
# ============================================================

def generate_main_factors(recognition_result: Dict[str, Any]) -> List[str]:
    """
    根据识别结果生成人类可读的判断依据列表

    输入：recognize_sport_business() 的返回结果
    输出：自然语言描述的依据列表
    """
    factors = []
    feature_weights = recognition_result.get("feature_weights", {})
    w1 = feature_weights.get("w1_business_scope", 0)
    w2 = feature_weights.get("w2_keyword_density", 0)
    w3 = feature_weights.get("w3_code_weight", 0)
    w4 = feature_weights.get("w4_category_coverage", 0)

    total_lines = recognition_result.get("total_business_lines", 0)
    sport_lines = recognition_result.get("sport_business_lines", 0)
    sport_lines_detail = recognition_result.get("sport_lines", [])
    keywords = recognition_result.get("keywords", [])
    code_type = recognition_result.get("code_type", "none")
    crossover_type = recognition_result.get("crossover_type", "")

    # 1. 业务线维度
    if total_lines > 0:
        if sport_lines == total_lines:
            factors.append(f"全部{total_lines}条业务线均为体育业务")
        elif sport_lines > 0:
            factors.append(f"{total_lines}条业务线中{sport_lines}条为体育业务（占比{sport_lines/total_lines:.0%}）")
            # 列出体育业务线关键词
            sport_line_texts = [
                sl.get("line", "")[:20]
                for sl in (sport_lines_detail or [])[:3]
                if sl.get("line")
            ]
            if sport_line_texts:
                factors.append(f"体育业务线包括：{'、'.join(sport_line_texts)}")
    else:
        factors.append("无法从业务文本中拆分出业务线")

    # 2. 关键词维度
    if keywords:
        top_keywords = keywords[:5]
        factors.append(f"命中{len(keywords)}个体育关键词：{'、'.join(top_keywords)}")
    else:
        factors.append("业务文本中未命中体育关键词")

    # 3. 行业代码维度
    if code_type == "direct":
        factors.append("行业代码为直接体育相关（代码权重高）")
    elif code_type == "indirect":
        factors.append("行业代码为间接体育相关（可能存在跨界经营）")
    else:
        factors.append("行业代码不属于体育分类（纯文本识别）")

    # 4. 业态覆盖
    all_cats = recognition_result.get("all_sport_categories", [])
    if len(all_cats) >= 2:
        factors.append(f"涉及{len(all_cats)}类体育业态：{'、'.join(all_cats)}")
    elif len(all_cats) == 1:
        factors.append(f"集中在单一体育业态：{all_cats[0]}")

    # 5. 跨界信息
    if crossover_type:
        factors.append(f"跨界类型：{crossover_type}")

    return factors


# ============================================================
# 核心比重估计函数
# ============================================================

def estimate_sport_share(
    recognition_result: Dict[str, Any],
    enterprise_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    基于识别结果计算 SportShare

    输入：
      recognition_result: recognize_sport_business() 的返回结果
      enterprise_info: 企业附加信息（规模等级等），可选

    返回：
      {
          model_share, share_band, share_band_label,
          lower_bound, upper_bound, model_confidence,
          main_factors, sport_category, ...
      }
    """
    sport_ratio = recognition_result.get("sport_ratio", 0.0)
    confidence = recognition_result.get("confidence", 0.0)
    sport_category = recognition_result.get("sport_category", "")
    is_sport = recognition_result.get("is_sport", False)
    code_type = recognition_result.get("code_type", "none")
    total_lines = recognition_result.get("total_business_lines", 0)
    sport_lines = recognition_result.get("sport_business_lines", 0)

    if not is_sport:
        return {
            "model_share": 0.0,
            "share_band": "very_low",
            "share_band_label": "极低比重",
            "lower_bound": 0.0,
            "upper_bound": 0.0,
            "model_confidence": 0.0,
            "main_factors": ["该企业未被识别为体育企业"],
            "sport_category": "",
        }

    # 比重档位
    band = get_share_band(sport_ratio)

    # 预测区间
    lower, upper = calculate_confidence_interval(
        sport_ratio, confidence, sport_lines, total_lines, code_type
    )

    # 主要依据
    main_factors = generate_main_factors(recognition_result)

    return {
        "model_share": round(sport_ratio, 4),
        "share_band": band["key"],
        "share_band_label": band["label"],
        "share_band_color": band["color"],
        "share_band_description": band["description"],
        "lower_bound": lower,
        "upper_bound": upper,
        "model_confidence": round(confidence, 4),
        "main_factors": main_factors,
        "sport_category": sport_category,
        "is_sport": is_sport,
        "code_type": code_type,
    }


def batch_estimate_share(
    recognition_results: List[Dict[str, Any]],
    enterprises_info: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """批量比重估计"""
    results = []
    for i, rec in enumerate(recognition_results):
        ent_info = enterprises_info[i] if enterprises_info and i < len(enterprises_info) else None
        share_result = estimate_sport_share(rec, ent_info)
        # 携带原始标识
        share_result["credit_code"] = rec.get("credit_code", "")
        share_result["enterprise_name"] = rec.get("enterprise_name", "")
        share_result["industry_code"] = rec.get("industry_code", "")
        results.append(share_result)
    return results


def get_share_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """比重结果统计"""
    total = len(results)
    sport_results = [r for r in results if r.get("is_sport")]
    sport_count = len(sport_results)

    # 档位分布
    band_dist = {}
    for r in sport_results:
        band = r.get("share_band", "very_low")
        band_dist[band] = band_dist.get(band, 0) + 1

    # 分业态平均比重
    category_shares = {}
    category_counts = {}
    for r in sport_results:
        cat = r.get("sport_category", "其他")
        share = r.get("model_share", 0)
        if cat not in category_shares:
            category_shares[cat] = 0.0
            category_counts[cat] = 0
        category_shares[cat] += share
        category_counts[cat] += 1

    category_avg = {
        cat: round(category_shares[cat] / category_counts[cat], 4)
        for cat in category_shares
    }

    # 总体平均比重
    all_shares = [r.get("model_share", 0) for r in sport_results]
    avg_share = sum(all_shares) / len(all_shares) if all_shares else 0.0

    return {
        "total_enterprises": total,
        "estimated_count": sport_count,
        "avg_share": round(avg_share, 4),
        "band_distribution": band_dist,
        "category_avg_share": category_avg,
    }


def apply_manual_adjustment(
    share_result: Dict[str, Any],
    manual_value: float,
    adjusted_by: str,
    reason: str = "",
) -> Dict[str, Any]:
    """应用人工校准"""
    manual_value = max(0.0, min(1.0, manual_value))
    band = get_share_band(manual_value)

    return {
        **share_result,
        "manual_share": round(manual_value, 4),
        "is_manual_adjusted": True,
        "adjusted_by": adjusted_by,
        "adjusted_reason": reason,
        "manual_share_band": band["key"],
        "manual_share_band_label": band["label"],
    }
