"""
产业规模测算服务 v1.0

核心公式：企业体育业务规模 = 企业总体规模 × SportShare

支持多种规模字段：
  - 营业收入（正式收入测算 — 最优先）
  - 从业人数（正式从业测算）
  - 资产总额（正式资产测算）
  - 注册资本（代理规模估算）
  - 企业规模等级（代理规模估算）

输出三种口径：
  - formal:       基于营业收入的正式测算
  - proxy:        基于注册资本的代理估算
  - relative_index: 仅有比重的相对指数
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from services.output_calc import extract_region


# ============================================================
# 规模字段配置
# ============================================================

SCALE_FIELD_CONFIG = {
    "revenue": {
        "key": "revenue",
        "label": "营业收入",
        "unit": "万元",
        "priority": 1,
        "measurement_type": "formal",
        "measurement_label": "正式收入测算",
        "description": "基于企业营业收入 × SportShare",
    },
    "employee": {
        "key": "employee",
        "label": "从业人数",
        "unit": "人",
        "priority": 2,
        "measurement_type": "formal",
        "measurement_label": "正式从业测算",
        "description": "基于企业从业人数 × SportShare",
    },
    "asset": {
        "key": "asset",
        "label": "资产总额",
        "unit": "万元",
        "priority": 3,
        "measurement_type": "formal",
        "measurement_label": "正式资产测算",
        "description": "基于企业资产总额 × SportShare",
    },
    "capital": {
        "key": "capital",
        "label": "注册资本",
        "unit": "万元",
        "priority": 4,
        "measurement_type": "proxy",
        "measurement_label": "代理规模估算",
        "description": "基于注册资本推算（营业收入不可用时的替代方案）",
    },
    "scale_level": {
        "key": "scale_level",
        "label": "企业规模等级",
        "unit": "等级",
        "priority": 5,
        "measurement_type": "proxy",
        "measurement_label": "代理规模估算",
        "description": "基于企业规模等级的序数估算",
    },
    "relative_index": {
        "key": "relative_index",
        "label": "产出指数",
        "unit": "指数",
        "priority": 6,
        "measurement_type": "relative_index",
        "measurement_label": "样本内相对指数",
        "description": "SportShare × 100，不可加总为绝对规模，仅可排序对比",
    },
}

# 规模等级 → 营收估算（万元）
SCALE_LEVEL_ESTIMATES = {
    "大型": 50000,
    "中型": 5000,
    "小型": 500,
    "微型": 50,
    "未知": 500,
}


# ============================================================
# 核心计算函数
# ============================================================

def pick_scale_field(
    enterprise: Dict[str, Any],
    preferred_field: str = "auto",
) -> Tuple[str, float, str]:
    """
    智能选择可用的最优规模字段

    按优先级：营业收入 > 从业人数 > 资产总额 > 注册资本 > 规模等级 > 相对指数

    Returns: (field_key, field_value, measurement_type)
    """
    if preferred_field != "auto" and preferred_field in SCALE_FIELD_CONFIG:
        val = _extract_field_value(enterprise, preferred_field)
        if val is not None and val > 0:
            cfg = SCALE_FIELD_CONFIG[preferred_field]
            return (preferred_field, val, cfg["measurement_type"])

    # 按优先级自动选择
    for field_key in ["revenue", "employee", "asset", "capital"]:
        cfg = SCALE_FIELD_CONFIG[field_key]
        val = _extract_field_value(enterprise, field_key)
        if val is not None and val > 0:
            return (field_key, val, cfg["measurement_type"])

    # 尝试规模等级
    scale_level = enterprise.get("scale_level", "")
    if scale_level and scale_level in SCALE_LEVEL_ESTIMATES:
        return ("scale_level", SCALE_LEVEL_ESTIMATES[scale_level], "proxy")

    # 兜底：相对指数
    return ("relative_index", 0.0, "relative_index")


def _extract_field_value(enterprise: Dict[str, Any], field_key: str) -> Optional[float]:
    """从企业字典中提取规模字段值"""
    key_mapping = {
        "revenue": ["total_revenue", "营业收入", "营收"],
        "employee": ["employee_count", "从业人数", "员工人数", "职工人数"],
        "asset": ["total_assets", "资产总额", "总资产"],
        "capital": ["registered_capital", "注册资本", "注册资金"],
    }
    keys = key_mapping.get(field_key, [field_key])
    for k in keys:
        val = enterprise.get(k)
        if val is not None:
            try:
                fv = float(val)
                if fv > 0:
                    return fv
            except (ValueError, TypeError):
                continue
    return None


def calculate_enterprise_sport_scale(
    enterprise: Dict[str, Any],
    share_result: Dict[str, Any],
    preferred_field: str = "auto",
) -> Dict[str, Any]:
    """
    计算单企业体育业务规模

    Returns:
        {
            enterprise_id, credit_code, enterprise_name,
            scale_field_type, scale_field_value, scale_field_label,
            sport_share_used, sport_scale,
            measurement_type, measurement_label,
        }
    """
    # 选择规模字段
    field_key, field_value, measurement_type = pick_scale_field(enterprise, preferred_field)
    field_cfg = SCALE_FIELD_CONFIG.get(field_key, SCALE_FIELD_CONFIG["relative_index"])

    # 获取 SportShare
    sport_share = share_result.get("manual_share") or share_result.get("model_share") or 0.0

    # 计算体育业务规模
    sport_scale = field_value * sport_share

    return {
        "enterprise_id": enterprise.get("id") or enterprise.get("enterprise_id"),
        "credit_code": enterprise.get("credit_code", ""),
        "enterprise_name": enterprise.get("name") or enterprise.get("enterprise_name", ""),
        "scale_field_type": field_key,
        "scale_field_value": round(field_value, 2),
        "scale_field_label": field_cfg["label"],
        "scale_field_unit": field_cfg["unit"],
        "sport_share_used": round(sport_share, 4),
        "sport_scale": round(sport_scale, 2),
        "measurement_type": measurement_type,
        "measurement_label": field_cfg["measurement_label"],
        "sport_category": share_result.get("sport_category", ""),
    }


def batch_calculate_scale(
    enterprises: List[Dict[str, Any]],
    share_results: List[Dict[str, Any]],
    preferred_field: str = "auto",
) -> List[Dict[str, Any]]:
    """批量计算企业体育业务规模"""
    results = []
    for i, ent in enumerate(enterprises):
        share = share_results[i] if i < len(share_results) else {}
        scale_result = calculate_enterprise_sport_scale(ent, share, preferred_field)
        results.append(scale_result)
    return results


# ============================================================
# 汇总分析
# ============================================================

def aggregate_regional_scale(
    enterprises: List[Dict[str, Any]],
    share_results: List[Dict[str, Any]],
    scale_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """按市州汇总体育产业规模"""
    region_data: Dict[str, Dict] = defaultdict(lambda: {
        "total_enterprises": 0,
        "sport_enterprises": 0,
        "total_scale": 0.0,
        "categories": defaultdict(float),
        "crossover_count": 0,
    })

    for i, ent in enumerate(enterprises):
        name = ent.get("name", ent.get("enterprise_name", ""))
        region = extract_region(name)
        share = share_results[i] if i < len(share_results) else {}
        scale = scale_results[i] if i < len(scale_results) else {}

        is_sport = share.get("is_sport", False) or share.get("model_share", 0) > 0
        if not is_sport:
            continue

        region_data[region]["sport_enterprises"] += 1
        region_data[region]["total_scale"] += scale.get("sport_scale", 0)
        cat = share.get("sport_category", "其他")
        region_data[region]["categories"][cat] += scale.get("sport_scale", 0)
        if share.get("crossover_type"):
            region_data[region]["crossover_count"] += 1

    # 计算每个区域的总企业数
    for ent in enterprises:
        name = ent.get("name", ent.get("enterprise_name", ""))
        region = extract_region(name)
        region_data[region]["total_enterprises"] += 1

    results = []
    for region, data in sorted(region_data.items(), key=lambda x: -x[1]["sport_enterprises"]):
        sport_count = data["sport_enterprises"]
        dominant_cat = max(data["categories"], key=data["categories"].get) if data["categories"] else ""
        crossover_rate = data["crossover_count"] / sport_count if sport_count > 0 else 0

        results.append({
            "region": region,
            "region_type": "city" if "市" in region else "district",
            "total_enterprises": data["total_enterprises"],
            "sport_enterprises": sport_count,
            "estimated_scale": round(data["total_scale"], 2),
            "dominant_category": dominant_cat,
            "crossover_rate": round(crossover_rate, 4),
            "new_candidates": sport_count,
            "high_risk_review_count": 0,
        })

    return results


def compare_methods(
    enterprises: List[Dict[str, Any]],
    scale_results: List[Dict[str, Any]],
    share_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    对比传统代码法与 SportFusion 融合测算法

    传统方法：仅统计行业代码为 direct sport code 的企业
    SportFusion：统计所有候选企业 × SportShare
    """
    from utils.industry_code import is_direct_sport_code

    traditional_scale = 0.0
    traditional_count = 0
    fusion_scale = 0.0
    fusion_count = 0

    for i, ent in enumerate(enterprises):
        code = ent.get("industry_code")
        is_direct = is_direct_sport_code(code) if code else False
        scale = scale_results[i] if i < len(scale_results) else {}
        share = share_results[i] if i < len(share_results) else {}

        sport_scale = scale.get("sport_scale", 0)

        if is_direct:
            traditional_scale += sport_scale
            traditional_count += 1

        if share.get("is_sport") or share.get("model_share", 0) > 0:
            fusion_scale += sport_scale
            fusion_count += 1

    incremental = fusion_scale - traditional_scale
    incremental_pct = (incremental / traditional_scale * 100) if traditional_scale > 0 else 0

    return {
        "traditional": {
            "scale": round(traditional_scale, 2),
            "enterprise_count": traditional_count,
            "method": "传统代码法",
            "description": "仅统计直接体育行业代码企业",
        },
        "fusion": {
            "scale": round(fusion_scale, 2),
            "enterprise_count": fusion_count,
            "method": "SportFusion 融合测算法",
            "description": "基于文本识别+行业代码+SportShare的综合测算",
        },
        "incremental_scale": round(incremental, 2),
        "incremental_pct": round(incremental_pct, 1),
        "new_enterprises": fusion_count - traditional_count,
    }


def calculate_category_scale(
    scale_results: List[Dict[str, Any]],
    share_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """计算九类业态各自的规模"""
    cat_data: Dict[str, Dict] = defaultdict(lambda: {"scale": 0.0, "count": 0})

    for i, scale in enumerate(scale_results):
        share = share_results[i] if i < len(share_results) else {}
        cat = share.get("sport_category", "其他")
        if cat == "非体育":
            continue
        cat_data[cat]["scale"] += scale.get("sport_scale", 0)
        cat_data[cat]["count"] += 1

    total = sum(d["scale"] for d in cat_data.values())

    results = []
    for cat, data in sorted(cat_data.items(), key=lambda x: -x[1]["scale"]):
        results.append({
            "category": cat,
            "enterprise_count": data["count"],
            "estimated_scale": round(data["scale"], 2),
            "share_pct": round(data["scale"] / total * 100, 2) if total > 0 else 0,
        })

    return results


def get_measurement_type_summary(scale_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """统计各口径的企业数量和规模"""
    formal_count = sum(1 for r in scale_results if r.get("measurement_type") == "formal")
    proxy_count = sum(1 for r in scale_results if r.get("measurement_type") == "proxy")
    relative_count = sum(1 for r in scale_results if r.get("measurement_type") == "relative_index")
    total = len(scale_results)

    # 确定主导口径
    if formal_count > total * 0.5:
        dominant_type = "formal"
        dominant_label = "正式收入测算"
    elif proxy_count > total * 0.5:
        dominant_type = "proxy"
        dominant_label = "代理规模估算"
    else:
        dominant_type = "relative_index"
        dominant_label = "样本内相对指数"

    return {
        "dominant_type": dominant_type,
        "dominant_label": dominant_label,
        "coverage_rate": round((formal_count + proxy_count) / total * 100, 1) if total > 0 else 0,
        "formal_count": formal_count,
        "proxy_count": proxy_count,
        "relative_count": relative_count,
        "total_count": total,
    }
