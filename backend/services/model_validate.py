"""
模型验证服务 — 对比传统行业代码统计方法 vs 文本+代码融合识别方法
"""

from typing import List, Dict, Any
from collections import defaultdict


def compare_methods(
    enterprises: List[Dict],
    recognition_results: List[Dict],
) -> Dict[str, Any]:
    """
    对比两种方法：

    1. 传统方法：仅依据行业代码判定（direct sport code → 100% 体育，其余 → 0%）
    2. 模型方法：文本+代码融合识别（continuous ratio 0-1）

    Args:
        enterprises: 原始企业数据 [{"name", "industry_code", "business_text"}, ...]
        recognition_results: 模型识别结果 [{...sport_ratio, is_sport, ...}, ...]
    """
    total = len(enterprises)

    # === 传统方法 ===
    from utils.industry_code import is_direct_sport_code, is_any_sport_code

    traditional_binary = []  # 0/1 判定
    traditional_detailed = []  # 带分类

    for ent in enterprises:
        code = ent.get("industry_code")
        is_sport = is_direct_sport_code(code) if code else False
        traditional_binary.append(1 if is_sport else 0)
        traditional_detailed.append({
            "is_sport": is_sport,
            "method": "传统行业代码法",
            "basis": f"行业代码{code}",
        })

    # === 模型方法 ===
    model_sport = []
    for r in recognition_results:
        model_sport.append({
            "is_sport": r.get("is_sport", False),
            "sport_ratio": r.get("sport_score", r.get("sport_ratio", 0.0)),
            "method": "文本+代码融合识别",
            "basis": f"业务边界:{r.get('sport_business_lines', 0)}/{r.get('total_business_lines', 0)}, 置信度:{r.get('confidence', 0)}",
        })

    # === 指标计算 ===
    # 传统法识别的体育企业数
    trad_count = sum(1 for t in traditional_binary if t == 1)
    # 模型法识别的体育企业数
    model_count = sum(1 for m in model_sport if m["is_sport"])
    # 两种方法都识别为体育的
    both_count = sum(
        1 for t, m in zip(traditional_binary, model_sport)
        if t == 1 and m["is_sport"]
    )
    # 仅传统法识别的
    only_trad = sum(
        1 for t, m in zip(traditional_binary, model_sport)
        if t == 1 and not m["is_sport"]
    )
    # 仅模型法识别的（跨界/文本发现）
    only_model = sum(
        1 for t, m in zip(traditional_binary, model_sport)
        if t == 0 and m["is_sport"]
    )

    # 模型法独有的增量企业
    incremental = []
    for i, (t, m) in enumerate(zip(traditional_binary, model_sport)):
        if t == 0 and m["is_sport"]:
            incremental.append({
                "name": enterprises[i].get("name", ""),
                "industry_code": enterprises[i].get("industry_code"),
                "sport_ratio": m["sport_ratio"],
                "confidence": recognition_results[i].get("confidence", 0),
                "category": recognition_results[i].get("sport_category", ""),
                "crossover_type": recognition_results[i].get("crossover_type", ""),
            })

    # 传统法遗漏（在传统法中标记为体育但模型认为低比重）
    low_ratio_in_trad = []
    for i, (t, m) in enumerate(zip(traditional_binary, model_sport)):
        if t == 1 and m["is_sport"] and m.get("sport_ratio", 0) < 0.3:
            low_ratio_in_trad.append({
                "name": enterprises[i].get("name", ""),
                "industry_code": enterprises[i].get("industry_code"),
                "sport_ratio": m["sport_ratio"],
            })

    # === 比重分布对比 ===
    # 传统法: 只有 0 或 1
    trad_ratio_dist = {"0": total - trad_count, "1.0": trad_count}

    # 模型法: 连续分布
    model_ratio_bins = {"0": 0, "0-0.2": 0, "0.2-0.5": 0, "0.5-0.8": 0, "0.8-1.0": 0}
    for m in model_sport:
        ratio = m.get("sport_ratio", 0)
        if ratio == 0:
            model_ratio_bins["0"] += 1
        elif ratio <= 0.2:
            model_ratio_bins["0-0.2"] += 1
        elif ratio <= 0.5:
            model_ratio_bins["0.2-0.5"] += 1
        elif ratio <= 0.8:
            model_ratio_bins["0.5-0.8"] += 1
        else:
            model_ratio_bins["0.8-1.0"] += 1

    # === 业态分类对比 ===
    trad_category_dist: Dict[str, int] = defaultdict(int)
    model_category_dist: Dict[str, int] = defaultdict(int)
    from utils.industry_code import get_sport_category

    for ent in enterprises:
        code = ent.get("industry_code")
        if code and is_direct_sport_code(code):
            cat = get_sport_category(code) or "其他"
            trad_category_dist[cat] += 1

    for r in recognition_results:
        if r.get("is_sport"):
            cat = r.get("sport_category", "非体育")
            model_category_dist[cat] += 1

    # === 跨界经营发现 ===
    crossover_by_model = sum(1 for r in recognition_results if r.get("is_crossover"))

    return {
        "comparison_summary": {
            "total_enterprises": total,
            "traditional_sport_count": trad_count,
            "traditional_sport_pct": round(trad_count / total * 100, 2) if total > 0 else 0,
            "model_sport_count": model_count,
            "model_sport_pct": round(model_count / total * 100, 2) if total > 0 else 0,
            "both_agree": both_count,
            "only_traditional": only_trad,
            "only_model": only_model,
            "incremental_count": len(incremental),
            "incremental_pct": round(len(incremental) / total * 100, 2) if total > 0 else 0,
            "crossover_discovered": crossover_by_model,
            "low_ratio_in_traditional": len(low_ratio_in_trad),
            "model_avg_ratio": round(
                sum(m.get("sport_ratio", 0) for m in model_sport if m["is_sport"])
                / max(model_count, 1), 4
            ),
        },
        "ratio_distribution_comparison": {
            "traditional": trad_ratio_dist,
            "model": model_ratio_bins,
        },
        "category_comparison": {
            "traditional": dict(trad_category_dist),
            "model": dict(model_category_dist),
        },
        "incremental_enterprises": incremental[:100],  # Top 100 增量发现
        "low_ratio_in_traditional_enterprises": low_ratio_in_trad[:50],
        "conclusion": _generate_conclusion(
            total, trad_count, model_count, only_model, crossover_by_model
        ),
    }


def _generate_conclusion(
    total: int, trad: int, model: int, incremental: int, crossover: int
) -> Dict[str, str]:
    """生成对比结论"""
    conclusions = {}

    if model > trad:
        conclusions["coverage"] = (
            f"模型法较传统行业代码法多识别 {model - trad} 家体育企业"
            f"（提升 {(model-trad)/max(trad,1)*100:.1f}%），"
            f"其中纯跨界经营 {crossover} 家，"
            f"证明传统方法存在显著低估"
        )
    else:
        conclusions["coverage"] = (
            f"模型法识别数量与传统法基本一致，但提供了连续的比重分布"
            f"（传统法仅有0/1二值），更精确反映企业实际体育业务占比"
        )

    if incremental > 0:
        conclusions["incremental"] = (
            f"模型法发现 {incremental} 家传统方法无法识别的体育业务企业，"
            f"占总量的 {incremental/total*100:.2f}%，"
            f"这些企业的行业代码非体育但实际经营包含体育业务"
        )

    if crossover > 0:
        conclusions["crossover"] = (
            f"识别出 {crossover} 家跨界经营企业，"
            f"验证了多元经营背景下传统行业代码法的局限性"
        )

    return conclusions
