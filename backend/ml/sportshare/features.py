"""
SportShare feature builder — leakage-safe feature vector.

CRITICAL: SportShareFeatureVector must NOT contain fields that directly
reconstruct the target T_i = sport_business_lines / total_business_lines.

Explicitly excluded (leakage prevention):
    - w1_business_scope (sport_lines / total_lines ≡ target proxy)
    - sport_business_lines / total_business_lines ratio
    - Any equivalent reconstruction of the structural target
"""

from dataclasses import dataclass, field

from domain.industry_code import normalize_industry_code
from services.business_line_service import (
    classify_business_line,
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

    Does NOT include w1_business_scope or any direct T_i reconstruction.
    Derived from SportFeatureVector with explicit leakage removal.
    """

    # ---- 关键词特征 (no business-line ratio) ----
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

    # ---- 派生特征 ----
    code_type: str = "none"
    sport_score: float = 0.0  # SportScore as input (NOT as target)
    keyword_density_raw: float = 0.0

    # ---- 业务线关键词分布 (不泄露比例) ----
    sport_keywords_matched: list[str] = field(default_factory=list)

    # ---- 元数据 ----
    quality_flags: list[str] = field(default_factory=list)


def build_sportshare_features(
    business_text: str,
    industry_code: str | float | None = None,
    sport_score: float = 0.0,
) -> SportShareFeatureVector:
    """
    Build leakage-safe SportShare feature vector.

    Explicitly does NOT include w1_business_scope or any field
    that directly encodes sport_business_lines / total_business_lines.

    This ensures the RF model learns structural patterns,
    not a trivial identity mapping to the target T_i.
    """
    fv = SportShareFeatureVector()
    fv.sport_score = sport_score

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
        fv.code_type = "none"
        fv.w3_code_weight = 0.0

    # ---- Category coverage ----
    sport_cats = set()
    for kw in keywords:
        from services.business_line_service import get_category_for_word
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

    Feature order (deterministic):
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
        10: sport_score
        11: keyword_density_raw
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
        fv.sport_score,
        fv.keyword_density_raw,
    ]


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
    "sport_score",
    "keyword_density_raw",
]
