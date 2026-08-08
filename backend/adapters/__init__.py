"""
Legacy compatibility adapter for old sport_ratio consumers.

Phase 1 policy:
    - Domain services output ONLY sport_score
    - This adapter maps sport_score → legacy sport_ratio where needed
    - All legacy_* functions are explicitly deprecated

DO NOT import from this module in new code.
DO NOT use legacy_sport_ratio in domain/service logic.

Usage (only for old API consumers that haven't migrated yet):
    from adapters.legacy_recognition import to_legacy_result
    legacy = to_legacy_result(recognition_result)
"""

from typing import Any


def to_legacy_result(result: dict[str, Any]) -> dict[str, Any]:
    """
    将现代识别结果映射为旧接口兼容格式。

    现代字段 sport_score 被复制到旧字段名 sport_ratio。
    此函数为 deprecated，仅用于旧 API 版本过渡。

    Deprecated: Phase 3 正式移除。
    """
    legacy = dict(result)
    # Ensure legacy sport_ratio exists for old consumers
    if "sport_score" in legacy and "sport_ratio" not in legacy:
        legacy["sport_ratio"] = legacy["sport_score"]
    return legacy


def legacy_sport_ratio_from_score(sport_score: float) -> float:
    """
    Deprecated: 从 SportScore 获取旧 sport_ratio 值。

    当前阶段 sport_ratio ≡ sport_score（identity mapping）。
    仅用于旧接口兼容，不应出现在新的业务逻辑中。
    """
    return sport_score
