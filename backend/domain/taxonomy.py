"""
体育业态分类 — 唯一权威 taxonomy

项目内所有模块必须从这里获取业态分类定义。
不得在其他文件中自行定义九类名称或映射。

九类业态（与正式数据字典一致）：
    体育赛事       SPORT_EVENT
    健身休闲       FITNESS_RECREATION
    体育用品       SPORT_GOODS
    体育培训       SPORT_TRAINING
    体育场馆       SPORT_VENUE
    体育传媒       SPORT_MEDIA
    体育管理       SPORT_MANAGEMENT
    电子竞技       ESPORTS
    体育彩票       SPORT_LOTTERY
"""

from enum import Enum


class SportCategory(str, Enum):
    """体育业态分类枚举 — 内部使用稳定 ID"""

    SPORT_EVENT = "sport_event"
    FITNESS_RECREATION = "fitness_recreation"
    SPORT_GOODS = "sport_goods"
    SPORT_TRAINING = "sport_training"
    SPORT_VENUE = "sport_venue"
    SPORT_MEDIA = "sport_media"
    SPORT_MANAGEMENT = "sport_management"
    ESPORTS = "esports"
    SPORT_LOTTERY = "sport_lottery"


# 中文名称映射（API 层使用）
CATEGORY_LABELS_ZH: dict[SportCategory, str] = {
    SportCategory.SPORT_EVENT: "体育赛事",
    SportCategory.FITNESS_RECREATION: "健身休闲",
    SportCategory.SPORT_GOODS: "体育用品",
    SportCategory.SPORT_TRAINING: "体育培训",
    SportCategory.SPORT_VENUE: "体育场馆",
    SportCategory.SPORT_MEDIA: "体育传媒",
    SportCategory.SPORT_MANAGEMENT: "体育管理",
    SportCategory.ESPORTS: "电子竞技",
    SportCategory.SPORT_LOTTERY: "体育彩票",
}

# 反向映射：中文 → Enum
CATEGORY_FROM_ZH: dict[str, SportCategory] = {v: k for k, v in CATEGORY_LABELS_ZH.items()}

# 英文 key → Enum
CATEGORY_FROM_KEY: dict[str, SportCategory] = {c.value: c for c in SportCategory}

# 规范 ID 列表
CANONICAL_CATEGORY_IDS = sorted(c.value for c in SportCategory)

# 规范中文名列表
CANONICAL_CATEGORY_NAMES = sorted(CATEGORY_LABELS_ZH.values())


def get_category_enum(identifier: str) -> SportCategory | None:
    """
    从任意标识符解析 SportCategory。
    支持：枚举值 ("sport_event")、中文名 ("体育赛事")、enum member name ("SPORT_EVENT")
    """
    if identifier in CATEGORY_FROM_KEY:
        return CATEGORY_FROM_KEY[identifier]
    if identifier in CATEGORY_FROM_ZH:
        return CATEGORY_FROM_ZH[identifier]
    try:
        return SportCategory[identifier]
    except (KeyError, ValueError):
        return None


def is_valid_category(identifier: str) -> bool:
    """检查标识符是否为有效业态分类"""
    return get_category_enum(identifier) is not None
