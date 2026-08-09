"""
SportShare feature builder — leakage-safe feature vector.

CRITICAL: SportShareFeatureVector must NOT contain:
    - w1_business_scope (direct T_i proxy)
    - sport_score (indirect T_i proxy via W1 = 0.40 * sport_lines/total_lines)
    - sport_business_lines / total_business_lines (target itself)
    - Any field that directly or indirectly reconstructs T_i

Allowed features (no leakage path to T_i):
    - Keyword density / term stats (text signal, not line-ratio)
    - Industry code weights (external prior)
    - Category coverage (diversity, not ratio)
    - Text/business-line counts (scale, not ratio)
"""

from dataclasses import dataclass, field

from domain.industry_code import normalize_industry_code
from services.business_line_service import (
    classify_business_line,
    get_category_for_word,
    get_sport_categories,
    match_sport_keywords,
    parse_business_lines,
)
from services.text_normalization_service import normalize_text
from utils.industry_code import get_code_type


@dataclass
class SportShareFeatureVector:
    """
    Leakage-safe feature vector for SportShare estimation.

    Explicitly excluded (SportScore removed Phase 3 closure):
        - w1_business_scope
        - sport_score (contains 0.40*W1 → leaks T_i)
        - sport_business_lines / total_business_lines
    """

    # ---- 关键词特征 ----
    w2_keyword_density: float = 0.0
    sport_term_count: int = 0
    token_count: int = 0

    # ---- 行业代码证据 ----
    w3_code_weight: float = 0.0
    direct_code_support: bool = False
    indirect_code_support: bool = False

    # ---- 业态覆盖 ----
    w4_category_coverage: float = 0.0
    category_count: int = 0
    primary_sport_category: str = ""

    # ---- 文本特征 ----
    text_length: int = 0
    business_line_count: int = 0

    # ---- 关键词原始密度 ----
    keyword_density_raw: float = 0.0

    # ---- 业务线关键词分布 ----
    sport_keywords_matched: list[str] = field(default_factory=list)

    # ---- 元数据 ----
    quality_flags: list[str] = field(default_factory=list)


# Canonical feature names — must NOT contain w1_business_scope or sport_score
FEATURE_NAMES = [
    "w2_keyword_density",
    "sport_term_count",
    "token_count",
    "w3_code_weight",
    "direct_code_support",
    "indirect_code_support",
    "w4_category_coverage",
    "category_count",
    "text_length",
    "business_line_count",
    "keyword_density_raw",
]


def build_sportshare_features(
    business_text: str,
    industry_code: str | float | None = None,
) -> SportShareFeatureVector:
    """
    Build leakage-safe SportShare feature vector.

    Does NOT accept or use sport_score — removed for indirect T_i leakage.
    """
    fv = SportShareFeatureVector()

    # ---- Text normalization ----
    text = normalize_text(business_text) if business_text else ""
    fv.text_length = len(text)

    if not text or len(text) < 2:
        return fv

    # ---- Business lines (structural info, NO ratio) ----
    business_lines = parse_business_lines(text)
    fv.business_line_count = len(business_lines)

    # ---- Keywords (presence/type, not line-ratio) ----
    keywords = match_sport_keywords(text)
    fv.sport_keywords_matched = keywords
    fv.sport_term_count = len(keywords)

    import re
    tokens = re.sub(r"[^一-鿿a-zA-Z0-9]", " ", text).split()
    token_count = len(tokens) if tokens else 1
    fv.token_count = token_count
    fv.w2_keyword_density = min(fv.sport_term_count / token_count * 10.0, 1.0)
    fv.keyword_density_raw = fv.sport_term_count / token_count if token_count > 0 else 0.0

    # ---- Industry code ----
    norm_code = normalize_industry_code(industry_code)
    if norm_code is not None:
        fv.code_type = get_code_type(norm_code)
        fv.direct_code_support = fv.code_type == "direct"
        fv.indirect_code_support = fv.code_type == "indirect"
        fv.w3_code_weight = 0.85 if fv.direct_code_support else (0.30 if fv.indirect_code_support else 0.0)
    else:
        fv.w3_code_weight = 0.0

    # ---- Category coverage ----
    sport_cats: set[str] = set()
    for kw in keywords:
        cat = get_category_for_word(kw)
        if cat:
            sport_cats.add(cat)
    fv.category_count = len(sport_cats)
    all_cats = get_sport_categories()
    fv.w4_category_coverage = len(sport_cats) / len(all_cats) if all_cats else 0.0

    # ---- Primary category ----
    classified = [classify_business_line(line) for line in business_lines]
    sport_lines = [c for c in classified if c["is_sport"]]
    cat_counts: dict[str, int] = {}
    for sl in sport_lines:
        cat = sl["category"]
        if cat:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
    fv.primary_sport_category = max(cat_counts, key=cat_counts.get) if cat_counts else ""

    return fv


def sportshare_features_to_array(fv: SportShareFeatureVector) -> list[float]:
    """
    Convert SportShareFeatureVector to a fixed-order float array for RF input.

    Feature order (deterministic, 11 features, NO sport_score):
        0: w2_keyword_density
        1: sport_term_count
        2: token_count
        3: w3_code_weight
        4: direct_code_support (0/1)
        5: indirect_code_support (0/1)
        6: w4_category_coverage
        7: category_count
        8: text_length
        9: business_line_count
        10: keyword_density_raw
    """
    return [
        fv.w2_keyword_density,
        float(fv.sport_term_count),
        float(fv.token_count),
        fv.w3_code_weight,
        1.0 if fv.direct_code_support else 0.0,
        1.0 if fv.indirect_code_support else 0.0,
        fv.w4_category_coverage,
        float(fv.category_count),
        float(fv.text_length),
        float(fv.business_line_count),
        fv.keyword_density_raw,
    ]
