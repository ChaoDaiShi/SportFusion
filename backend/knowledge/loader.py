"""
知识库加载器 — 从版本化 JSON 文件加载体育词典、行业代码映射等。

这是项目中唯一负责加载知识库配置的模块。
其他模块不得自行读取 JSON 文件或硬编码知识数据。
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_KNOWLEDGE_DIR = Path(__file__).resolve().parent
_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@lru_cache(maxsize=1)
def load_sports_dictionary() -> dict[str, Any]:
    """加载体育业务词典"""
    path = _KNOWLEDGE_DIR / "sports_dictionary.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_industry_codes() -> dict[str, Any]:
    """加载行业代码映射"""
    path = _KNOWLEDGE_DIR / "industry_codes.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_model_params() -> dict[str, Any]:
    """加载模型参数配置"""
    path = _CONFIG_DIR / "model_params.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_knowledge_versions() -> dict[str, Any]:
    """加载知识版本清单"""
    path = _CONFIG_DIR / "knowledge_versions.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_active_version_metadata() -> dict[str, str]:
    """
    返回当前激活的知识版本元数据，
    用于附加到识别结果中。
    """
    manifest = load_knowledge_versions()
    return dict(manifest.get("versions", {}))


def get_enabled_terms() -> list[dict]:
    """获取所有启用的词条"""
    data = load_sports_dictionary()
    return [t for t in data.get("terms", []) if t.get("enabled", True)]


def get_term_index() -> dict[str, dict]:
    """
    构建 term → metadata 索引。
    Key 为词条文本，Value 为完整的词条元数据。
    """
    terms = get_enabled_terms()
    index: dict[str, dict] = {}
    for t in terms:
        index[t["term"]] = t
        for alias in t.get("aliases", []):
            if alias not in index:
                index[alias] = t
    return index


def get_industry_code_index() -> dict[int, dict]:
    """构建 code → metadata 索引"""
    data = load_industry_codes()
    index: dict[int, dict] = {}
    for c in data.get("codes", []):
        if c.get("enabled", True):
            index[c["code"]] = c
    return index


def get_feature_weights() -> dict[str, float]:
    """获取 W1-W4 权重配置"""
    params = load_model_params()
    return dict(params.get("feature_weights", {}))


def get_code_type_weight(code_type: str) -> float:
    """获取行业代码类型对应的证据权重"""
    params = load_model_params()
    return float(params.get("code_type_weights", {}).get(code_type, 0.0))
