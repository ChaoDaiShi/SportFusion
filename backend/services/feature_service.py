"""
特征工程服务 — Phase 2 canonical SportFeatureVector and unified builder

这是整个项目中唯一负责构建 W1-W4 特征向量的模块。
所有模型（recognition、SportShare、validation、review priority）
必须从这里获取特征向量。

SportFeatureVector 包含:
    - W1-W4 四维特征
    - 业务线统计
    - 关键词统计
    - 行业代码证据
    - 业态覆盖度
    - 派生字段 (code_type, evidence_relation, primary_category)
    - 数据质量标记
    - 版本元数据
"""

from dataclasses import dataclass, field
from typing import Any

from domain.evidence_relation import derive_evidence_relation
from domain.industry_code import normalize_industry_code
from knowledge.loader import (
    get_active_version_metadata,
    get_code_type_weight,
    get_feature_weights,
)
from utils.industry_code import get_code_type

from services.business_line_service import (
    classify_business_line,
    get_category_for_word,
    get_sport_categories,
    match_sport_keywords,
    parse_business_lines,
)
from services.text_normalization_service import is_empty_or_noise, normalize_text


@dataclass
class SportFeatureVector:
    """
    统一体育特征向量 — 所有模型消费的标准特征结构。

    字段分组:
        W1-W4: 四维评分特征 [0, 1]
        Business Lines: 业务线统计
        Keywords: 关键词统计
        Code: 行业代码证据
        Categories: 业态覆盖
        Derived: 派生字段
        Quality: 数据质量标记
        Meta: 版本元数据
    """

    # ---- W1-W4 特征 [0, 1] ----
    w1_business_scope: float = 0.0
    w2_keyword_density: float = 0.0
    w3_code_weight: float = 0.0
    w4_category_coverage: float = 0.0

    # ---- 业务线统计 ----
    total_business_lines: int = 0
    sport_business_lines: int = 0
    business_lines: list[str] = field(default_factory=list)
    sport_lines_detail: list[dict] = field(default_factory=list)
    non_sport_lines: list[str] = field(default_factory=list)

    # ---- 关键词统计 ----
    sport_term_count: int = 0
    token_count: int = 0
    sport_keywords_matched: list[str] = field(default_factory=list)

    # ---- 行业代码证据 ----
    direct_code_support: bool = False
    indirect_code_support: bool = False

    # ---- 业态覆盖 ----
    category_count: int = 0
    primary_sport_category: str = ""
    all_sport_categories: list[str] = field(default_factory=list)

    # ---- 文本属性 ----
    text_length: int = 0
    business_line_count: int = 0

    # ---- 派生字段 ----
    code_type: str = "none"
    evidence_relation: str = ""
    normalized_text: str = ""

    # ---- 数据质量 ----
    quality_flags: list[str] = field(default_factory=list)

    # ---- 版本元数据 ----
    version_metadata: dict[str, str] = field(default_factory=dict)


def build_feature_vector(
    business_text: str,
    industry_code: str | float | None = None,
    enterprise_name: str | None = None,
) -> SportFeatureVector:
    """
    统一特征构建器 — 整个项目唯一的 W1-W4 计算入口。

    所有模型模块必须从这里获取特征向量，
    不得各自重复实现 parse_business_lines / calculate_sport_ratio 等逻辑。

    Args:
        business_text: 企业主营业务描述文本
        industry_code: 行业代码（支持 int/str/float/None）
        enterprise_name: 企业名称（可选，用于未来扩展）

    Returns:
        SportFeatureVector — 完整的标准化特征向量
    """
    fv = SportFeatureVector()
    fv.version_metadata = get_active_version_metadata()

    # ---- 文本标准化 ----
    text = normalize_text(business_text) if business_text else ""
    fv.normalized_text = text
    fv.text_length = len(text)

    # ---- 数据质量检测 ----
    _detect_quality_issues(fv, business_text, industry_code)

    # ---- 行业代码处理 ----
    norm_code = normalize_industry_code(industry_code)
    if norm_code is not None:
        fv.code_type = get_code_type(norm_code)
        fv.direct_code_support = fv.code_type == "direct"
        fv.indirect_code_support = fv.code_type == "indirect"
        fv.w3_code_weight = get_code_type_weight(fv.code_type)
    else:
        fv.code_type = "none"
        fv.w3_code_weight = 0.0

    # 空文本快速路径
    if is_empty_or_noise(text):
        return fv

    # ---- 业务线解析 (调用统一 pipeline) ----
    business_lines = parse_business_lines(text)
    classified = [classify_business_line(line) for line in business_lines]
    sport_lines = [c for c in classified if c["is_sport"]]
    fv.total_business_lines = len(business_lines)
    fv.sport_business_lines = len(sport_lines)
    fv.business_lines = business_lines
    fv.sport_lines_detail = sport_lines
    fv.non_sport_lines = [c["line"] for c in classified if not c["is_sport"]]
    fv.business_line_count = len(business_lines)

    # ---- W1: 业务范围占比 ----
    if fv.total_business_lines > 0:
        fv.w1_business_scope = fv.sport_business_lines / fv.total_business_lines

    # ---- 关键词匹配 (调用统一匹配函数) ----
    all_keywords = match_sport_keywords(text)
    fv.sport_keywords_matched = all_keywords
    fv.sport_term_count = len(all_keywords)

    # ---- W2: 关键词密度 ----
    import re

    from services.business_line_service import normalize_text as _norm
    _tokens = re.sub(r"[^一-鿿a-zA-Z0-9]", " ", _norm(text)).split()
    token_count = len(_tokens) if _tokens else 1
    fv.token_count = token_count
    keyword_density_norm = get_feature_weights().get("_density_normalizer", 10.0)
    if "keyword_density_normalizer" not in str(get_feature_weights()):
        keyword_density_norm = 10.0  # Phase 1 compat default
    fv.w2_keyword_density = min(fv.sport_term_count / token_count * keyword_density_norm, 1.0)

    # ---- W4: 业态覆盖度 ----
    sport_cats = set()
    for kw in all_keywords:
        cat = get_category_for_word(kw)
        if cat:
            sport_cats.add(cat)
    all_cats = get_sport_categories()
    fv.category_count = len(sport_cats)
    fv.all_sport_categories = list(sport_cats)
    if all_cats:
        fv.w4_category_coverage = len(sport_cats) / len(all_cats)

    # ---- 主要业态 ----
    cat_counts: dict[str, int] = {}
    for sl in sport_lines:
        cat = sl["category"]
        if cat:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
    fv.primary_sport_category = max(cat_counts, key=cat_counts.get) if cat_counts else ""

    # ---- EvidenceRelation ----
    text_evidence = len(all_keywords) > 0
    w3w = get_feature_weights().get("w3_code_weight", 0.25)
    w4w = get_feature_weights().get("w4_category_coverage", 0.10)
    w1w = get_feature_weights().get("w1_business_scope", 0.40)
    w2w = get_feature_weights().get("w2_keyword_density", 0.25)
    sport_score_raw = w1w * fv.w1_business_scope + w2w * fv.w2_keyword_density + w3w * fv.w3_code_weight + w4w * fv.w4_category_coverage
    sport_score_raw = round(min(sport_score_raw, 1.0), 4)

    fv.evidence_relation = derive_evidence_relation(
        code_type=fv.code_type,
        text_evidence=text_evidence,
        sport_score=sport_score_raw,
        keyword_count=len(all_keywords),
    ).value

    return fv


def _detect_quality_issues(fv: SportFeatureVector, raw_text: Any, raw_code: Any) -> None:
    """检测数据质量问题并记录到 FeatureVector"""
    flags = []

    if raw_text is None or (isinstance(raw_text, str) and not raw_text.strip()):
        flags.append("missing_business_text")
    elif isinstance(raw_text, str) and len(raw_text.strip()) < 2:
        flags.append("empty_business_lines")

    if raw_code is not None:
        try:
            nc = normalize_industry_code(raw_code)
            if nc is None and raw_code not in (None, ""):
                flags.append("invalid_industry_code")
        except Exception:
            flags.append("invalid_industry_code")

    if fv.business_line_count == 0 and fv.text_length >= 2:
        flags.append("empty_business_lines")

    if fv.sport_term_count == 0 and fv.w3_code_weight == 0:
        flags.append("no_sport_signal")

    fv.quality_flags = flags
