"""行业代码映射 — GB/T 4754-2017 国民经济行业分类中与体育产业相关的代码

设计思路：
  - 直接体育行业代码：企业主营业务明确是体育 → 高置信度
  - 间接相关行业代码：企业可能涉及体育（如教育、广告、软件）→ 需文本辅助确认
  - 非体育行业：仅靠文本关键词匹配识别跨界经营
"""

from typing import Optional, Dict, List, Set

# ============================================================
# 1. 直接体育行业代码（GB/T 4754-2017 明确体育类）
#    这些行业代码对应的企业主营业务就是体育
# ============================================================
DIRECT_SPORT_CODES: Dict[int, str] = {
    # === 体育组织管理 ===
    8911: "体育管理",       # 体育组织（体育协会、职业体育俱乐部等）
    8912: "体育管理",       # 体育社团
    8919: "体育管理",       # 其他体育组织
    # === 体育场馆设施 ===
    8921: "体育场馆",       # 体育场馆管理
    8929: "体育场馆",       # 其他体育场地设施管理
    # === 健身休闲活动 ===
    8930: "健身休闲",       # 健身休闲活动
    # === 体育培训 ===
    8392: "体育培训",       # 体校及体育培训
    # === 体育用品制造 ===
    2441: "体育用品",       # 球类制造
    2442: "体育用品",       # 体育器材及配件制造
    2443: "体育用品",       # 训练健身器材制造
    2444: "体育用品",       # 运动防护用具制造
    2449: "体育用品",       # 其他体育用品制造
    1821: "体育用品",       # 运动机织服装制造
    1831: "体育用品",       # 运动针织服装制造
    # === 体育用品销售 ===
    5142: "体育用品",       # 体育用品及器材批发
    5242: "体育用品",       # 体育用品及器材零售
    # === 体育设备租赁 ===
    7121: "体育场馆",       # 体育设备出租
    # === 体育设施工程 ===
    4892: "体育场馆",       # 体育场地设施工程施工
}

# ============================================================
# 2. 间接相关行业代码（可能含体育业务，需文本辅助确认）
#    这些行业代码下只有部分企业与体育相关
# ============================================================
INDIRECT_SPORT_CODES: Dict[int, str] = {
    # 教育类（含体育培训，但不全是）
    8391: "体育培训",       # 职业技能培训（可能含体育教练培训）
    8399: "体育培训",       # 其他未列明教育（可能含体育培训）
    8331: "体育培训",       # 普通初中教育（可能含体校）
    8341: "体育培训",       # 普通小学教育（可能含体育特色校）
    # 服装鞋帽制造（可能含运动类）
    1952: "体育用品",       # 运动皮鞋制造
    1954: "体育用品",       # 运动橡胶鞋制造
    1961: "体育用品",       # 运动塑料鞋制造
    # 零售类（可能含体育用品）
    5238: "体育用品",       # 鞋帽零售（可能含运动鞋服）
    # 传媒类（可能含体育内容）
    8720: "体育传媒",       # 电视（可能含体育频道）
    8622: "体育传媒",       # 期刊出版（可能含体育期刊）
    8612: "体育传媒",       # 图书出版（可能含体育图书）
    8810: "体育传媒",       # 录音制作（可能含体育内容）
    # 广告营销（可能含体育营销）
    7259: "体育管理",       # 其他广告服务（可能含体育广告/营销）
    7251: "体育管理",       # 互联网广告服务（可能含体育推广）
    # 互联网/软件（可能含体育类产品）
    6513: "体育科技",       # 应用软件开发（可能含体育类APP）
    6450: "体育科技",       # 互联网数据服务（可能含体育数据）
    # 旅游（可能含体育旅游）
    7291: "体育旅游",       # 旅行社及相关服务（可能含体育旅游线路）
    # 咨询（可能含体育咨询）
    7249: "体育管理",       # 其他专业咨询与调查（可能含体育咨询）
}

# ============================================================
# 3. 行业名称映射（合并直接+间接）
# ============================================================
ALL_SPORT_CODES: Dict[int, str] = {}
ALL_SPORT_CODES.update(DIRECT_SPORT_CODES)
ALL_SPORT_CODES.update(INDIRECT_SPORT_CODES)

INDUSTRY_NAMES: Dict[int, str] = {
    8911: "体育组织", 8912: "体育社团", 8919: "其他体育组织",
    8921: "体育场馆管理", 8929: "其他体育场地设施管理",
    8930: "健身休闲活动",
    8392: "体校及体育培训", 8391: "职业技能培训",
    8399: "其他未列明教育", 8331: "普通初中教育", 8341: "普通小学教育",
    2441: "球类制造", 2442: "体育器材及配件制造",
    2443: "训练健身器材制造", 2444: "运动防护用具制造",
    2449: "其他体育用品制造", 1821: "运动机织服装制造", 1831: "运动针织服装制造",
    1952: "运动皮鞋制造", 1954: "运动橡胶鞋制造", 1961: "运动塑料鞋制造",
    5142: "体育用品及器材批发", 5242: "体育用品及器材零售", 5238: "鞋帽零售",
    7121: "体育设备出租", 4892: "体育场地设施工程施工",
    8720: "电视", 8622: "期刊出版", 8612: "图书出版", 8810: "录音制作",
    7259: "其他广告服务", 7251: "互联网广告服务",
    6513: "应用软件开发", 6450: "互联网数据服务",
    7291: "旅行社及相关服务", 7249: "其他专业咨询与调查",
}


def is_direct_sport_code(code: int) -> bool:
    """判断是否为直接体育行业代码（企业主营业务即体育）"""
    return code in DIRECT_SPORT_CODES


def is_indirect_sport_code(code: int) -> bool:
    """判断是否为间接相关行业代码（可能含体育，需文本辅助）"""
    return code in INDIRECT_SPORT_CODES


def is_any_sport_code(code: int) -> bool:
    """任一体育相关（直接或间接）"""
    return code in ALL_SPORT_CODES


def get_sport_category(code: int) -> Optional[str]:
    """获取行业代码对应的体育业态分类（直接>间接）"""
    return ALL_SPORT_CODES.get(code)


def get_code_type(code: int) -> str:
    """返回代码类型: 'direct' | 'indirect' | 'none'"""
    if code in DIRECT_SPORT_CODES:
        return "direct"
    elif code in INDIRECT_SPORT_CODES:
        return "indirect"
    return "none"


def get_industry_name(code: int) -> str:
    """获取行业代码对应的中文名称"""
    return INDUSTRY_NAMES.get(code, f"行业代码{code}")


def get_all_sport_codes() -> List[int]:
    """获取所有体育相关行业代码"""
    return sorted(ALL_SPORT_CODES.keys())


def get_direct_sport_codes() -> Set[int]:
    """获取直接体育代码集合"""
    return set(DIRECT_SPORT_CODES.keys())


def get_indirect_sport_codes() -> Set[int]:
    """获取间接体育代码集合"""
    return set(INDIRECT_SPORT_CODES.keys())


def classify_by_text_and_code(text: str, industry_code: int) -> Dict:
    """
    综合文本匹配 + 行业代码类型判断体育业务分类

    置信度规则：
      - 直接体育代码 + 文本匹配 → 0.95 (几乎确定)
      - 直接体育代码 + 无文本匹配 → 0.75 (代码明确，可能文本描述简略)
      - 间接代码 + 文本匹配 → 0.70 (跨界经营确认)
      - 间接代码 + 无文本匹配 → 0.0 (代码不特定，不标记)
      - 非体育代码 + 文本匹配 → 0.60 (纯跨界经营)
      - 非体育代码 + 无文本匹配 → 0.0 (与体育无关)

    Returns:
        {
            "is_sport": bool,
            "code_type": "direct"|"indirect"|"none",
            "text_has_sport": bool,
            "sport_category": str,
            "confidence": float,
        }
    """
    from utils.text_tokenizer import match_sport_by_category, has_sport_content

    code_type = get_code_type(industry_code)
    code_category = get_sport_category(industry_code) or ""
    text_has_sport = has_sport_content(text)
    text_categories = match_sport_by_category(text)

    # 综合判断
    if code_type == "direct":
        if text_has_sport:
            # 直接体育代码 + 文本也匹配 → 极高置信度
            confidence = 0.95
            sport_category = list(text_categories.keys())[0] if text_categories else code_category
        else:
            # 直接体育代码但文本未匹配 → 中高置信度（可能是简略描述或只写了"体育"类）
            confidence = 0.75
            sport_category = code_category
    elif code_type == "indirect":
        if text_has_sport:
            # 间接代码 + 文本匹配 → 跨界经营，中等置信度
            confidence = 0.70
            sport_category = list(text_categories.keys())[0]
        else:
            # 间接代码 + 无文本匹配 → 不标记为体育
            confidence = 0.0
            sport_category = ""
    else:
        if text_has_sport:
            # 非体育代码但文本有体育关键词 → 跨界经营
            confidence = 0.60
            sport_category = list(text_categories.keys())[0]
        else:
            confidence = 0.0
            sport_category = ""

    return {
        "is_sport": confidence > 0,
        "code_type": code_type,
        "code_is_direct": code_type == "direct",
        "code_is_indirect": code_type == "indirect",
        "text_has_sport": text_has_sport,
        "sport_category": sport_category,
        "code_category": code_category,
        "text_categories": {k: v for k, v in text_categories.items()},
        "confidence": round(confidence, 2),
    }
