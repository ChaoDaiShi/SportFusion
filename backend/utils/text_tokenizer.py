"""
文本分词工具 — Phase 2: delegates to knowledge base + business_line_service

保留旧 API 兼容，但实际逻辑委托给:
    - knowledge.loader (词典加载)
    - services.business_line_service (匹配/分类)
    - services.text_normalization_service (文本清理)

旧硬编码 SPORT_KEYWORDS_BY_CATEGORY 已迁移至:
    backend/knowledge/sports_dictionary.json

新增模块不应再从此文件导入；应使用 services.business_line_service。
"""


import jieba

# ---- 向后兼容：从知识库加载 ----
from knowledge.loader import load_sports_dictionary

_dict_data = load_sports_dictionary()
_cat_map = _dict_data.get("categories", {})

# 重建旧式 SPORT_KEYWORDS_BY_CATEGORY (兼容旧 import)
SPORT_KEYWORDS_BY_CATEGORY: dict[str, list[str]] = {}
for term_entry in _dict_data.get("terms", []):
    if term_entry.get("enabled", True):
        cat_zh = term_entry["category"]
        SPORT_KEYWORDS_BY_CATEGORY.setdefault(cat_zh, []).append(term_entry["term"])

# 扁平化关键词列表
SPORT_DICT: list[str] = []
for _cat, _words in SPORT_KEYWORDS_BY_CATEGORY.items():
    SPORT_DICT.extend(_words)

# 注册到 jieba
for word in SPORT_DICT:
    jieba.add_word(word)

# ---- 委托给统一服务 ----


def tokenize(text: str) -> list[str]:
    """分词（保留 jieba 行为兼容）"""
    import re
    if not text:
        return []
    text = re.sub(r"[^一-鿿a-zA-Z0-9]", " ", str(text))
    words = jieba.lcut(text)
    return [w.strip() for w in words if len(w.strip()) > 1]


def extract_keywords(text: str, top_k: int = 10) -> list[str]:
    """TF-IDF 关键词提取（保留兼容）"""
    if not text:
        return []
    return jieba.analyse.extract_tags(str(text), topK=top_k, withWeight=False)


def get_sport_dict() -> list[str]:
    """获取完整体育关键词列表"""
    return SPORT_DICT
