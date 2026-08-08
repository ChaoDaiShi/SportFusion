"""
行业代码标准化 — 统一入口

负责将所有可能的行业代码输入格式规范化为 int | None，
避免不同模块各自处理类型转换导致的不一致。

支持格式:
    - int:    8911
    - str:    "8911", " 8911 ", "8911.0", "NULL", "nan", ""
    - float:  8911.0
    - None

规则:
    - 8911 与 "8911" 行为完全一致
    - 非法值返回 None（不抛异常）
"""

import math


def normalize_industry_code(raw: str | float | None) -> int | None:
    """
    将行业代码输入规范化为 int | None。

    Args:
        raw: 原始行业代码值，可以是 str、int、float 或 None。

    Returns:
        规范化后的整数行业代码，如果无法解析则返回 None。

    Examples:
        >>> normalize_industry_code(8911)
        8911
        >>> normalize_industry_code("8911")
        8911
        >>> normalize_industry_code(" 8911 ")
        8911
        >>> normalize_industry_code(8911.0)
        8911
        >>> normalize_industry_code("8911.0")
        8911
        >>> normalize_industry_code(None)
        None
        >>> normalize_industry_code("")
        None
        >>> normalize_industry_code("NULL")
        None
        >>> normalize_industry_code("nan")
        None
        >>> normalize_industry_code("not_a_code")
        None
    """
    if raw is None:
        return None

    # Handle float inputs — strip fractional part; NaN/Inf → None
    if isinstance(raw, float):
        if math.isnan(raw) or math.isinf(raw):
            return None
        raw = int(raw)

    # Handle int directly
    if isinstance(raw, int):
        return raw

    # Handle string inputs
    if isinstance(raw, str):
        stripped = raw.strip()

        # Empty string → None
        if not stripped:
            return None

        # Sentinel null values
        if stripped.upper() in ("NULL", "NAN", "NONE", "NA", ""):
            return None

        # Try integer parse first
        try:
            return int(stripped)
        except ValueError:
            pass

        # Try float parse (e.g. "8911.0")
        try:
            fval = float(stripped)
            if math.isnan(fval) or math.isinf(fval):
                return None
            return int(fval)
        except (ValueError, OverflowError):
            pass

        # Cannot parse
        return None

    # Unknown type — cannot normalize
    return None
