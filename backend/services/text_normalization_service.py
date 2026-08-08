"""
文本标准化服务 — Phase 2 unified text normalization pipeline

职责:
    - 全角→半角转换
    - 多余空白清理
    - Unicode 规范化
    - 否定上下文检测
    - 异常输入安全处理

这是整个项目中唯一负责文本标准化的模块。
"""

import re
import unicodedata
from typing import Any

# 否定模式：匹配 "非/不得/除外/不涉及/不含" 等否定前缀
_NEGATION_PATTERNS = [
    re.compile(r"非[一-鿿]+"),
    re.compile(r"不得(?:从事|开展|经营|涉及)[一-鿿]+"),
    re.compile(r"[一-鿿]+除外"),
    re.compile(r"不含[一-鿿]+"),
    re.compile(r"不涉及[一-鿿]+"),
    re.compile(r"禁止[一-鿿]+"),
    re.compile(r"未从事[一-鿿]+"),
]


def normalize_text(text: Any) -> str:
    """
    文本标准化：安全处理任意输入，输出干净的规范化字符串。

    处理顺序:
        1. 类型安全：None → ""
        2. Unicode 规范化 (NFKC)
        3. 全角字符 → 半角字符
        4. 多余空白清理
        5. 控制字符移除
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Unicode NFKC 规范化
    text = unicodedata.normalize("NFKC", text)

    # 全角→半角
    result = []
    for ch in text:
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        elif code == 0x3000:  # 全角空格
            result.append(" ")
        else:
            result.append(ch)
    text = "".join(result)

    # 合并连续空白
    text = re.sub(r"\s+", " ", text)

    # 移除控制字符(保留换行)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    return text.strip()


def detect_negative_context(text: str) -> list[str]:
    """
    检测文本中的否定/排除语境片段。

    Returns:
        匹配到的否定片段列表（例如 ["非体育用品", "不得开展体育培训"]）
    """
    if not text:
        return []
    fragments = []
    for pattern in _NEGATION_PATTERNS:
        fragments.extend(pattern.findall(text))
    return fragments


def has_negative_context_for_term(text: str, term: str) -> bool:
    """
    检查特定词条在文本中是否处于否定语境中。

    例如：text="不得开展体育培训", term="体育培训" → True
    """
    fragments = detect_negative_context(text)
    for frag in fragments:
        if term in frag:
            return True
    return False


def clean_business_line(line: str) -> str:
    """
    清理单条业务线文本：
        - 去除首尾标点和空白
        - 移除仅含标点的行
        - 长度 < 2 返回空
    """
    if not line:
        return ""
    cleaned = re.sub(r"^[\s，,；;、/／。．\.\-—\-]+", "", line)
    cleaned = re.sub(r"[\s，,；;、/／。．\.\-—\-]+$", "", cleaned)
    cleaned = cleaned.strip()
    if len(cleaned) < 2:
        return ""
    return cleaned


def is_empty_or_noise(text: Any) -> bool:
    """判断文本是否为空或噪声"""
    if text is None:
        return True
    if not isinstance(text, str):
        text = str(text)
    cleaned = normalize_text(text)
    return len(cleaned) < 2
