"""
产业分析服务 v1.0
  - 区域聚合：城市/区县级体育产出指数
  - 业态聚合：9大业态产值分布
  - 空间集中度分析（CRn, HHI指数）
  - 产业结构特征分析
  - 发展态势指标生成
"""
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from services.output_calc import extract_region


def aggregate_by_region(
    results: List[Dict],
    enterprises: List[Dict],
) -> Dict[str, Any]:
    """
    按区域聚合体育产出指数

    Returns:
        {
            "region_stats": [{"region": str, "count": int, "sport_output": float, "avg_ratio": float}, ...],
            "city_stats": [...],
            "district_stats": [...],
        }
    """
    region_data: Dict[str, Dict] = defaultdict(lambda: {
        "count": 0, "total_output": 0.0, "total_ratio": 0.0,
        "categories": defaultdict(float),
    })

    for i, r in enumerate(results):
        if not r.get("is_sport"):
            continue
        name = enterprises[i].get("name", "") if i < len(enterprises) else ""
        region = extract_region(name)
        ratio = r.get("sport_score", r.get("sport_ratio", 0))
        output_idx = ratio * 100  # 产出指数
        cat = r.get("sport_category", "")

        region_data[region]["count"] += 1
        region_data[region]["total_output"] += output_idx
        region_data[region]["total_ratio"] += ratio
        region_data[region]["categories"][cat] += output_idx

    # 构建排名列表
    city_list = []
    district_list = []
    for reg, data in region_data.items():
        entry = {
            "region": reg,
            "enterprise_count": data["count"],
            "sport_output_index": round(data["total_output"], 2),
            "avg_sport_ratio": round(data["total_ratio"] / data["count"], 4) if data["count"] > 0 else 0,
            "category_breakdown": {
                cat: round(val, 2)
                for cat, val in sorted(data["categories"].items(), key=lambda x: -x[1])[:5]
            },
        }
        # 市级（含"市"字或地级市名称）
        if "市" in reg or len(reg) <= 3:
            city_list.append(entry)
        else:
            district_list.append(entry)

    city_list.sort(key=lambda x: -x["sport_output_index"])
    district_list.sort(key=lambda x: -x["sport_output_index"])

    return {
        "all_regions": sorted(
            city_list + district_list, key=lambda x: -x["sport_output_index"]
        ),
        "top_cities": city_list[:20],
        "top_districts": district_list[:20],
    }


def aggregate_by_category(results: List[Dict]) -> Dict[str, Any]:
    """按业态聚合体育产出"""
    cat_data: Dict[str, Dict] = defaultdict(lambda: {
        "count": 0, "total_output": 0.0, "total_ratio": 0.0, "crossover_count": 0,
    })

    for r in results:
        if not r.get("is_sport"):
            continue
        cat = r.get("sport_category", "其他")
        ratio = r.get("sport_score", r.get("sport_ratio", 0))
        output_idx = ratio * 100

        cat_data[cat]["count"] += 1
        cat_data[cat]["total_output"] += output_idx
        cat_data[cat]["total_ratio"] += ratio
        if r.get("is_crossover"):
            cat_data[cat]["crossover_count"] += 1

    categories = []
    total_output = sum(d["total_output"] for d in cat_data.values())
    for cat, data in sorted(cat_data.items(), key=lambda x: -x[1]["total_output"]):
        categories.append({
            "category": cat,
            "enterprise_count": data["count"],
            "output_index": round(data["total_output"], 2),
            "output_share_pct": round(data["total_output"] / total_output * 100, 2) if total_output > 0 else 0,
            "avg_sport_ratio": round(data["total_ratio"] / data["count"], 4) if data["count"] > 0 else 0,
            "crossover_count": data["crossover_count"],
            "crossover_pct": round(data["crossover_count"] / data["count"] * 100, 2) if data["count"] > 0 else 0,
        })

    return {
        "total_output_index": round(total_output, 2),
        "categories": categories,
    }


def spatial_concentration(region_stats: List[Dict]) -> Dict[str, Any]:
    """
    空间集中度分析

    指标:
      - CR3/CR5: 前3/5名区域集中度
      - HHI: 赫芬达尔指数（平方和 * 10000）
      - Gini系数: 简化版基尼系数
    """
    if not region_stats:
        return {"cr3": 0, "cr5": 0, "hhi": 0, "gini": 0}

    outputs = sorted([r["sport_output_index"] for r in region_stats], reverse=True)
    total = sum(outputs)
    if total == 0:
        return {"cr3": 0, "cr5": 0, "hhi": 0, "gini": 0}

    cr3 = sum(outputs[:3]) / total
    cr5 = sum(outputs[:5]) / total

    # HHI
    shares = [o / total for o in outputs]
    hhi = sum(s**2 for s in shares) * 10000

    # 简化基尼系数
    n = len(shares)
    gini = sum((2 * i - n - 1) * s for i, s in enumerate(sorted(shares), 1)) / n

    conclusion = ""
    if cr3 > 0.5:
        conclusion = f"高度集中：前3名区域占据 {cr3*100:.1f}% 的体育产出，呈现明显的中心-外围结构"
    elif cr3 > 0.3:
        conclusion = f"中度集中：前3名区域占据 {cr3*100:.1f}% 的体育产出，分布较为均衡"
    else:
        conclusion = f"较为分散：前3名区域占据 {cr3*100:.1f}% 的体育产出，呈现多点分布格局"

    return {
        "cr3": round(cr3, 4),
        "cr5": round(cr5, 4),
        "cr3_pct": round(cr3 * 100, 1),
        "cr5_pct": round(cr5 * 100, 1),
        "hhi": round(hhi, 1),
        "gini": round(gini, 4),
        "total_regions": len(region_stats),
        "conclusion": conclusion,
    }


def industry_structure_analysis(
    stats: Dict,
    region_stats: List[Dict],
    category_stats: List[Dict],
) -> Dict[str, Any]:
    """
    产业结构特征分析

    指标:
      - 业态多样性指数（Shannon entropy）
      - 主导业态及占比
      - 跨界经营率
      - 区域专业化程度
    """
    import math

    # 多样性指数
    shares = [c["output_share_pct"] / 100 for c in category_stats if c["output_share_pct"] > 0]
    entropy = -sum(s * math.log(s) for s in shares) if shares else 0
    max_entropy = math.log(len(shares)) if shares else 1
    diversity_idx = entropy / max_entropy if max_entropy > 0 else 0

    # 主导业态
    dominant = category_stats[0] if category_stats else None

    # 跨界率
    total_sport = stats.get("sport_count", 1)
    crossover_rate = stats.get("crossover_count", 0) / total_sport if total_sport > 0 else 0

    # 区域专业化：每个区域的最高业态占比
    region_specialization = []
    for reg in region_stats[:10]:
        if reg.get("category_breakdown"):
            top_cat = max(reg["category_breakdown"], key=reg["category_breakdown"].get)
            top_share = reg["category_breakdown"][top_cat] / reg["sport_output_index"] if reg["sport_output_index"] > 0 else 0
            region_specialization.append({
                "region": reg["region"],
                "dominant_category": top_cat,
                "dominant_share_pct": round(top_share * 100, 1),
            })

    # 均衡度评价
    if diversity_idx > 0.8:
        balance = "业态高度多元，结构均衡"
    elif diversity_idx > 0.5:
        balance = "业态较为多元，存在主导业态"
    elif diversity_idx > 0.3:
        balance = "业态相对集中，少数业态占主导"
    else:
        balance = "业态高度集中，结构单一"

    return {
        "diversity_index": round(diversity_idx, 4),
        "entropy": round(entropy, 4),
        "category_count": len(category_stats),
        "dominant_category": {
            "name": dominant["category"] if dominant else "",
            "share_pct": dominant["output_share_pct"] if dominant else 0,
        } if dominant else None,
        "crossover_rate_pct": round(crossover_rate * 100, 2),
        "balance_assessment": balance,
        "region_specialization": region_specialization,
    }


def generate_analysis_report(
    results: List[Dict],
    enterprises: List[Dict],
) -> Dict[str, Any]:
    """生成完整产业分析报告"""
    from services.sport_recognition import get_recognition_stats

    # 基础统计
    stats = get_recognition_stats(results)

    # 区域聚合
    region_result = aggregate_by_region(results, enterprises)

    # 业态聚合
    category_result = aggregate_by_category(results)

    # 空间集中度
    concentration = spatial_concentration(region_result["all_regions"])

    # 产业结构
    structure = industry_structure_analysis(
        stats, region_result["all_regions"], category_result["categories"]
    )

    return {
        "overview": {
            "total_enterprises": stats["total"],
            "sport_enterprises": stats["sport_count"],
            "sport_ratio_pct": stats["sport_ratio_pct"],
            "crossover_count": stats["crossover_count"],
            "crossover_pct": stats["crossover_pct"],
            "avg_sport_ratio_pct": stats["avg_sport_ratio_pct"],
            "total_output_index": category_result["total_output_index"],
        },
        "regional_analysis": {
            "top_cities": region_result["top_cities"][:10],
            "top_districts": region_result["top_districts"][:10],
            "spatial_concentration": concentration,
        },
        "category_analysis": {
            "categories": category_result["categories"],
        },
        "structure_analysis": structure,
        "data_quality": {
            "region_coverage": len(region_result["all_regions"]),
            "regions_with_data": len([r for r in region_result["all_regions"] if r["enterprise_count"] > 0]),
        },
    }
