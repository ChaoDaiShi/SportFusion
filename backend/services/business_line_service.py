"""
业务线解析服务 — Phase 2 unified business line parsing pipeline

Standard pipeline:
    raw_text → normalize_text → split → clean → deduplicate → classify → structured

这是整个项目中唯一负责业务线解析的模块。
sport_recognition.py 不得再自行实现 parse_business_lines() 或 classify_business_line()。
"""

import re
from typing import Any

from domain.taxonomy import CATEGORY_FROM_ZH
from knowledge.loader import get_term_index

from services.text_normalization_service import (
    clean_business_line,
    has_negative_context_for_term,
    normalize_text,
)

# 业务线分隔符（保持与 Phase 1 行为兼容）
_BUSINESS_LINE_SEPARATORS = re.compile(r"[，,；;、/／\n\r。；;．\.\s]+")


def parse_business_lines(text: Any) -> list[str]:
    """
    将「主要业务活动」文本拆分为独立的业务线。

    Pipeline:
        1. normalize_text()       — 全角→半角、Unicode 规范化
        2. split on separators    — 按常见业务分隔符拆分
        3. clean_business_line()  — 清理标点、过滤过短片段
        4. deduplicate            — 去重保持顺序（大小写敏感）
    """
    text = normalize_text(text)
    if not text or len(text) < 2:
        return []

    parts = _BUSINESS_LINE_SEPARATORS.split(text)
    lines = []
    for part in parts:
        cleaned = clean_business_line(part)
        if cleaned:
            lines.append(cleaned)

    # 去重保持顺序
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    return unique


def classify_business_line(line: str) -> dict[str, Any]:
    """
    判断单条业务线是否属于体育业务。

    使用知识库词条索引，考虑权重和否定上下文。

    Returns:
        {
            "line": str,
            "normalized_text": str,
            "is_sport": bool,
            "category": str,          # 中文业态名
            "category_id": str | None, # SportCategory.value
            "matched_terms": [str],
            "matched_term_details": [dict],
            "evidence_strength": float, # 0-1
        }
    """
    term_index = get_term_index()
    result: dict[str, Any] = {
        "line": line,
        "normalized_text": normalize_text(line),
        "is_sport": False,
        "category": "",
        "category_id": None,
        "matched_terms": [],
        "matched_term_details": [],
        "keywords": [],       # backward compat
        "evidence_strength": 0.0,
        "score": 0.0,          # backward compat
    }

    if not line or len(line) < 2:
        return result

    # 在全文中搜索每个启用词条
    matched: list[dict] = []
    for term_text, metadata in term_index.items():
        if term_text in line:
            # 检查否定上下文
            if has_negative_context_for_term(line, term_text):
                continue
            # 检查词条自身的 negative_context 列表
            neg_contexts = metadata.get("negative_context", [])
            blocked = False
            for neg in neg_contexts:
                if neg in line:
                    blocked = True
                    break
            if blocked:
                continue

            matched.append({
                "term": term_text,
                "category": metadata["category"],
                "weight": metadata.get("weight", 1.0),
                "ambiguity_level": metadata.get("ambiguity_level", "low"),
            })

    if not matched:
        return result

    # 按类别统计加权命中
    cat_scores: dict[str, float] = {}
    for m in matched:
        cat = m["category"]
        cat_scores[cat] = cat_scores.get(cat, 0.0) + m["weight"]

    # 最佳类别
    if cat_scores:
        best_cat = max(cat_scores, key=cat_scores.get)
        result["is_sport"] = True
        result["category"] = best_cat
        cat_enum = CATEGORY_FROM_ZH.get(best_cat)
        result["category_id"] = cat_enum.value if cat_enum else None

    result["matched_terms"] = [m["term"] for m in matched]
    result["matched_term_details"] = matched
    result["keywords"] = result["matched_terms"]  # backward compat

    # 证据强度：加权命中数 / 3 (保持与 Phase 1 兼容)
    total_weight = sum(m["weight"] for m in matched)
    result["evidence_strength"] = round(min(total_weight / 3.0, 1.0), 2)
    result["score"] = result["evidence_strength"]  # backward compat

    return result


def match_sport_keywords(text: str) -> list[str]:
    """
    匹配文本中所有体育关键词词条。

    使用知识库索引，考虑否定上下文。
    """
    term_index = get_term_index()
    if not text:
        return []
    text = normalize_text(text)

    matched = []
    seen = set()
    for term_text in term_index:
        if term_text in text and term_text not in seen:
            if has_negative_context_for_term(text, term_text):
                continue
            matched.append(term_text)
            seen.add(term_text)
    return matched


def match_sport_by_category(text: str) -> dict[str, list[str]]:
    """
    按业态分类匹配体育关键词。

    Returns:
        { "体育赛事": ["马拉松", "篮球赛"], ... }
    """
    matched_terms = match_sport_keywords(text)
    term_index = get_term_index()
    result: dict[str, list[str]] = {}
    for term_text in matched_terms:
        meta = term_index.get(term_text, {})
        cat = meta.get("category", "其他")
        result.setdefault(cat, []).append(term_text)
    return result


def get_sport_categories() -> list[str]:
    """获取所有体育业态中文名（来自知识库）"""
    from knowledge.loader import load_sports_dictionary
    data = load_sports_dictionary()
    return list(data.get("categories", {}).keys())


def get_category_for_word(word: str) -> str:
    """查询某个关键词属于哪个体育业态分类"""
    term_index = get_term_index()
    meta = term_index.get(word, {})
    return meta.get("category", "")


def has_sport_content(text: str) -> bool:
    """判断文本是否包含体育相关业务"""
    return len(match_sport_keywords(text)) > 0
