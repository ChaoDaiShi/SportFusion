"""NLP预处理服务 - 文本特征提取、体育业务分类、标签标注"""
from typing import List, Dict, Any, Optional
from utils.text_tokenizer import (
    tokenize, extract_keywords, match_sport_keywords,
    match_sport_by_category, has_sport_content, get_sport_categories,
)
from utils.industry_code import classify_by_text_and_code, is_any_sport_code, get_sport_category, get_code_type


def preprocess_business_text(text: str) -> Dict[str, Any]:
    """预处理企业主营业务文本（基础版：分词+关键词+体育词匹配）"""
    if not text:
        return {
            "tokens": [],
            "keywords": [],
            "sport_keywords": [],
            "sport_categories": {},
            "token_count": 0,
            "has_sport_content": False,
        }

    tokens = tokenize(text)
    keywords = extract_keywords(text, top_k=10)
    sport_keywords = match_sport_keywords(text)
    sport_categories = match_sport_by_category(text)

    return {
        "tokens": tokens,
        "keywords": keywords,
        "sport_keywords": sport_keywords,
        "sport_categories": sport_categories,
        "token_count": len(tokens),
        "has_sport_content": len(sport_keywords) > 0,
    }


def preprocess_enterprise(
    text: str,
    industry_code: Optional[int] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    完整的单条企业数据预处理（增强版：含行业代码辅助分类）

    Args:
        text: 主要业务活动文本
        industry_code: 行业代码（GB/T 4754）
        name: 企业名称（可选，用于从名称中提取特征）

    Returns:
        包含分词、关键词、体育标签、分类、特征等完整信息
    """
    result = preprocess_business_text(text)

    # 行业代码辅助分类
    if industry_code is not None:
        classification = classify_by_text_and_code(text, industry_code)
    else:
        classification = {
            "is_sport": result["has_sport_content"],
            "code_is_sport": False,
            "code_is_direct": False,
            "code_type": "none",
            "text_has_sport": result["has_sport_content"],
            "sport_category": list(result["sport_categories"].keys())[0] if result["sport_categories"] else "",
            "code_category": "",
            "text_categories": result["sport_categories"],
            "confidence": 0.7 if result["has_sport_content"] else 0.0,
        }

    # 从企业名称中提取体育特征
    name_sport_keywords = []
    if name:
        from utils.text_tokenizer import match_sport_keywords as msk
        name_sport_keywords = msk(name)

    # 特征工程
    text_len = len(str(text)) if text else 0
    sport_keyword_count = len(result["sport_keywords"])
    category_count = len(result["sport_categories"])

    result.update({
        "is_sport": classification["is_sport"],
        "sport_category": classification["sport_category"],
        "confidence": classification["confidence"],
        "code_type": classification["code_type"],
        "code_is_direct": classification["code_is_direct"],
        "code_category": classification["code_category"],
        "text_categories": classification["text_categories"],
        "name_sport_keywords": name_sport_keywords,
        # 特征指标
        "features": {
            "text_length": text_len,
            "token_count": len(result["tokens"]),
            "keyword_count": len(result["keywords"]),
            "sport_keyword_count": sport_keyword_count,
            "sport_category_count": category_count,
            "name_has_sport": len(name_sport_keywords) > 0,
        },
    })

    return result


def batch_preprocess(texts: List[str]) -> List[Dict[str, Any]]:
    """批量文本预处理（基础版）"""
    return [preprocess_business_text(t) for t in texts]


def batch_preprocess_enterprises(
    texts: List[str],
    industry_codes: Optional[List[Optional[int]]] = None,
    names: Optional[List[Optional[str]]] = None,
) -> List[Dict[str, Any]]:
    """批量企业数据预处理（增强版）"""
    results = []
    for i, text in enumerate(texts):
        code = industry_codes[i] if industry_codes else None
        name = names[i] if names else None
        results.append(preprocess_enterprise(text, code, name))
    return results


def get_preprocess_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """统计预处理结果"""
    total = len(results)
    sport_count = sum(1 for r in results if r.get("is_sport"))
    code_direct_count = sum(1 for r in results if r.get("code_is_direct"))
    code_indirect_count = sum(1 for r in results if r.get("code_type") == "indirect")
    text_sport_count = sum(1 for r in results if r.get("has_sport_content"))
    crossover_count = sum(
        1 for r in results
        if r.get("is_sport") and r.get("has_sport_content") and r.get("code_type") == "none"
    )

    # 业态分布
    category_dist: Dict[str, int] = {}
    for r in results:
        cat = r.get("sport_category", "")
        if cat:
            category_dist[cat] = category_dist.get(cat, 0) + 1

    # 置信度分布
    conf_bins = {"high": 0, "medium": 0, "low": 0}
    for r in results:
        c = r.get("confidence", 0)
        if c >= 0.8:
            conf_bins["high"] += 1
        elif c >= 0.5:
            conf_bins["medium"] += 1
        elif c > 0:
            conf_bins["low"] += 1

    return {
        "total": total,
        "sport_enterprise_count": sport_count,
        "sport_ratio": round(sport_count / total * 100, 2) if total > 0 else 0,
        "code_direct_count": code_direct_count,
        "code_indirect_count": code_indirect_count,
        "text_sport_count": text_sport_count,
        "crossover_count": crossover_count,  # 纯跨界经营（非体育代码+文本匹配）
        "category_distribution": category_dist,
        "confidence_distribution": conf_bins,
        "all_categories": get_sport_categories(),
    }
