"""产值测算服务 v2.0 — 基于体育业务比重的产业规模估算 + 区域提取"""
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict


def extract_region(name: str) -> str:
    """
    从企业名称中提取区域信息，返回标准化地级市/州名。
    无法匹配到具体城市的省级注册企业返回"四川省本级"。
    """
    if not name:
        return "四川省本级"

    name_str = str(name)

    # ── 第1步：直接匹配地级市/州（含市后缀标准化） ──
    city_patterns = [
        # 地级市（18个）
        (r"成都市?", "成都市"), (r"绵阳市?", "绵阳市"), (r"自贡市?", "自贡市"),
        (r"攀枝花市?", "攀枝花市"), (r"泸州市?", "泸州市"), (r"德阳市?", "德阳市"),
        (r"广元市?", "广元市"), (r"遂宁市?", "遂宁市"), (r"内江市?", "内江市"),
        (r"乐山市?", "乐山市"), (r"南充市?", "南充市"), (r"眉山市?", "眉山市"),
        (r"宜宾市?", "宜宾市"), (r"广安市?", "广安市"), (r"达州市?", "达州市"),
        (r"雅安市?", "雅安市"), (r"巴中市?", "巴中市"), (r"资阳市?", "资阳市"),
        # 自治州（3个）
        (r"凉山彝?族?自?治?州?|凉山", "凉山州"),
        (r"阿坝藏?族?羌?族?自?治?州?|阿坝", "阿坝州"),
        (r"甘孜藏?族?自?治?州?|甘孜", "甘孜州"),
        # 县级市（常见）
        (r"峨眉山市?", "峨眉山市"), (r"西昌市?", "西昌市"), (r"简阳市?", "简阳市"),
        (r"都江堰市?", "都江堰市"), (r"彭州市?", "彭州市"), (r"邛崃市?", "邛崃市"),
        (r"崇州市?", "崇州市"), (r"广汉市?", "广汉市"), (r"什邡市?", "什邡市"),
        (r"绵竹市?", "绵竹市"), (r"江油市?", "江油市"), (r"射洪市?", "射洪市"),
        (r"隆昌市?", "隆昌市"), (r"阆中市?", "阆中市"), (r"华蓥市?", "华蓥市"),
        (r"万源市?", "万源市"), (r"康定市?", "康定市"), (r"马尔康市?", "马尔康市"),
    ]
    for pattern, city_name in city_patterns:
        if re.search(pattern, name_str):
            return city_name

    # ── 第2步：区县级匹配——区名 → 上级地级市 ──
    district_to_city = {
        "锦江": "成都市", "青羊": "成都市", "金牛": "成都市", "武侯": "成都市",
        "成华": "成都市", "龙泉驿": "成都市", "青白江": "成都市", "新都": "成都市",
        "双流": "成都市", "郫都": "成都市", "温江": "成都市", "新津": "成都市",
        "高新": "成都市", "天府": "成都市", "蒲江": "成都市", "大邑": "成都市",
        "金堂": "成都市", "涪城": "绵阳市", "游仙": "绵阳市", "安州": "绵阳市",
        "旌阳": "德阳市", "罗江": "德阳市", "利州": "广元市", "昭化": "广元市",
        "朝天": "广元市", "船山": "遂宁市", "安居": "遂宁市", "中区": "内江市",
        "东兴": "内江市", "通川": "达州市", "达川": "达州市", "顺庆": "南充市",
        "高坪": "南充市", "嘉陵": "南充市", "翠屏": "宜宾市", "南溪": "宜宾市",
        "叙州": "宜宾市", "东坡": "眉山市", "彭山": "眉山市", "仁和": "攀枝花市",
        "东区攀": "攀枝花市", "西区攀": "攀枝花市", "雁江": "资阳市", "巴州": "巴中市",
        "恩阳": "巴中市", "雨城": "雅安市", "名山": "雅安市", "前锋": "广安市",
        "广安": "广安市", "龙马潭": "泸州市", "江阳": "泸州市", "纳溪": "泸州市",
    }
    district_match = re.search(r"([一-龥]{2,4}(?:区|县))", name_str)
    if district_match:
        district = district_match.group(1)
        for dist_key, city in district_to_city.items():
            if dist_key in district:
                return city
        # 成都地区的兜底匹配
        if "成都" in name_str:
            return "成都市"

    # ── 第3步：四川省注册但无具体城市 → 四川省本级 ──
    if re.search(r"(四川省|四川)", name_str):
        return "四川省本级"

    # ── 第4步：外省企业 ──
    province_match = re.search(
        r"(北京|上海|广东|浙江|江苏|湖北|重庆|天津|福建|山东|河南"
        r"|湖南|河北|辽宁|吉林|黑龙江|安徽|江西|山西|陕西|云南|贵州"
        r"|甘肃|青海|海南|广西|内蒙古|西藏|宁夏|新疆)",
        name_str,
    )
    if province_match:
        return province_match.group(1)

    # ── 第5步：完全无法识别 → 四川省本级（兜底） ──
    return "四川省本级"


def calculate_sport_output(
    sport_ratio: float,
    total_revenue: float = 0.0,
    industry_code: Optional[int] = None,
) -> Dict[str, Any]:
    """
    基于体育业务占比计算体育产值
    若无实际营收数据，使用归一化产出指数
    """
    if total_revenue > 0:
        sport_revenue = round(total_revenue * sport_ratio, 2)
        method = "实际营收"
    else:
        # 产出指数：将比重映射到 0-100 的指数（用于横向对比）
        sport_revenue = round(sport_ratio * 100, 2)
        total_revenue = 100.0
        method = "产出指数"

    return {
        "total_output": round(total_revenue, 2),
        "sport_output": sport_revenue,
        "sport_ratio": round(sport_ratio, 4),
        "method": method,
    }


def batch_calculate(items: List[dict]) -> Dict[str, Any]:
    """
    批量产业规模测算

    输入: [{"enterprise_id", "enterprise_name", "region", "sport_category",
            "total_revenue", "sport_ratio", "industry_code"}, ...]
    """
    results = []
    total_sport_revenue = 0.0
    region_stats = defaultdict(lambda: defaultdict(float))
    category_stats = defaultdict(float)

    for item in items:
        total_rev = item.get("total_revenue", 0.0)
        ratio = item.get("sport_ratio", item.get("sport_revenue_ratio", 0.0))
        output = calculate_sport_output(ratio, total_rev, item.get("industry_code"))

        result = {
            "enterprise_id": item.get("enterprise_id"),
            "enterprise_name": item.get("enterprise_name", ""),
            "region": item.get("region", "未知"),
            "sport_category": item.get("sport_category", "非体育"),
            "total_output": output["total_output"],
            "sport_output": output["sport_output"],
            "sport_ratio": output["sport_ratio"],
            "method": output["method"],
        }
        results.append(result)
        total_sport_revenue += output["sport_output"]

        region = item.get("region", "未知")
        category = item.get("sport_category", "非体育")
        region_stats[region]["total"] += output["total_output"]
        region_stats[region]["sport"] += output["sport_output"]
        region_stats[region]["count"] += 1
        category_stats[category] += output["sport_output"]

    # 区域汇总
    region_summary = []
    for region, stats in sorted(region_stats.items()):
        region_summary.append({
            "region": region,
            "total_output": round(stats["total"], 2),
            "sport_output": round(stats["sport"], 2),
            "enterprise_count": int(stats["count"]),
            "sport_ratio": round(stats["sport"] / stats["total"], 4) if stats["total"] > 0 else 0,
        })

    # 业态汇总
    category_summary = [
        {"category": cat, "sport_output": round(rev, 2)}
        for cat, rev in sorted(category_stats.items(), key=lambda x: -x[1])
    ]

    return {
        "results": results,
        "total_sport_output": round(total_sport_revenue, 2),
        "region_summary": region_summary,
        "category_summary": category_summary,
    }


def calculate_model_metrics(predicted: List[float], actual: List[float]) -> dict:
    """计算模型精度指标"""
    import numpy as np

    if not predicted or not actual or len(predicted) != len(actual):
        return {"mae": 0.0, "rmse": 0.0, "r2": 0.0}

    p = np.array(predicted)
    a = np.array(actual)

    mae = float(np.mean(np.abs(p - a)))
    rmse = float(np.sqrt(np.mean((p - a) ** 2)))
    ss_res = np.sum((a - p) ** 2)
    ss_tot = np.sum((a - np.mean(a)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot != 0 else 0.0

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
    }
