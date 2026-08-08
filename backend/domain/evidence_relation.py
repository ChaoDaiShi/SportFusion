"""
证据关系枚举与权威判断 — Phase 1 unified evidence_relation policy

定义统一的证据关系分类，提供唯一的推导函数。
所有模块（recognition, review, industry_code）统一从这里获得证据关系判断，
不再各自维护独立的 if/elif 规则。

EvidenceRelation 分类:
    DIRECT_CODE_TEXT_SUPPORT   — 直接体育代码 + 文本有体育证据 → 互相支持
    DIRECT_CODE_TEXT_WEAK      — 直接体育代码 + 文本无/弱证据 → 仅靠代码
    DIRECT_CODE_TEXT_CONFLICT  — 直接体育代码 + 但文本无体育关键词 → 代码-文本冲突

    INDIRECT_CODE_TEXT_SUPPORT — 间接代码 + 文本有体育证据 → 部分支持
    INDIRECT_CODE_TEXT_WEAK    — 间接代码 + 文本无/弱证据 → 证据不足

    TEXT_ONLY_SPORT            — 非体育代码 + 文本强体育信号 → 纯文本驱动

    NO_SPORT_EVIDENCE          — 既无代码也无文本体育证据
    INSUFFICIENT_INFORMATION   — 信息不足（空文本 + 非直接代码）
"""

from enum import Enum


class EvidenceRelation(str, Enum):
    DIRECT_CODE_TEXT_SUPPORT = "direct_code_text_support"
    DIRECT_CODE_TEXT_WEAK = "direct_code_text_weak"
    DIRECT_CODE_TEXT_CONFLICT = "direct_code_text_conflict"

    INDIRECT_CODE_TEXT_SUPPORT = "indirect_code_text_support"
    INDIRECT_CODE_TEXT_WEAK = "indirect_code_text_weak"

    TEXT_ONLY_SPORT = "text_only_sport"

    NO_SPORT_EVIDENCE = "no_sport_evidence"
    INSUFFICIENT_INFORMATION = "insufficient_information"


def derive_evidence_relation(
    code_type: str,
    text_evidence: bool,
    sport_score: float,
    keyword_count: int,
) -> EvidenceRelation:
    """
    权威证据关系推导函数 — 整个项目只在这一个地方判断 evidence_relation。

    Args:
        code_type:      'direct' | 'indirect' | 'none'
        text_evidence:  文本中是否匹配到体育关键词
        sport_score:    SportScore [0, 1]
        keyword_count:  匹配到的体育关键词数量

    Returns:
        EvidenceRelation 枚举值
    """
    if code_type == "direct":
        if text_evidence and sport_score >= 0.1:
            return EvidenceRelation.DIRECT_CODE_TEXT_SUPPORT
        elif text_evidence and sport_score < 0.1:
            return EvidenceRelation.DIRECT_CODE_TEXT_WEAK
        else:
            return EvidenceRelation.DIRECT_CODE_TEXT_CONFLICT

    elif code_type == "indirect":
        if text_evidence and sport_score >= 0.05:
            return EvidenceRelation.INDIRECT_CODE_TEXT_SUPPORT
        else:
            return EvidenceRelation.INDIRECT_CODE_TEXT_WEAK

    else:  # code_type == "none"
        if text_evidence and sport_score >= 0.10:
            return EvidenceRelation.TEXT_ONLY_SPORT
        elif not text_evidence and sport_score == 0.0:
            return EvidenceRelation.NO_SPORT_EVIDENCE
        elif not text_evidence and sport_score < 0.05:
            return EvidenceRelation.INSUFFICIENT_INFORMATION
        else:
            # Has some weak text signal but no code support
            return EvidenceRelation.INSUFFICIENT_INFORMATION


def derive_code_text_consistency(relation: EvidenceRelation) -> str:
    """
    从 EvidenceRelation 派生 code_text_consistency 字段。

    Returns:
        'consistent' | 'partial' | 'conflict' | 'unknown'
    """
    mapping = {
        EvidenceRelation.DIRECT_CODE_TEXT_SUPPORT: "consistent",
        EvidenceRelation.DIRECT_CODE_TEXT_WEAK: "partial",
        EvidenceRelation.DIRECT_CODE_TEXT_CONFLICT: "conflict",
        EvidenceRelation.INDIRECT_CODE_TEXT_SUPPORT: "partial",
        EvidenceRelation.INDIRECT_CODE_TEXT_WEAK: "partial",
        EvidenceRelation.TEXT_ONLY_SPORT: "conflict",
        EvidenceRelation.NO_SPORT_EVIDENCE: "consistent",
        EvidenceRelation.INSUFFICIENT_INFORMATION: "unknown",
    }
    return mapping.get(relation, "unknown")


def derive_crossover_type(relation: EvidenceRelation, sport_lines_count: int,
                          total_lines: int, is_sport: bool) -> str:
    """
    从 EvidenceRelation + 业务线结构派生 crossover_type。

    Returns:
        crossover_type 字符串（空字符串表示非跨界）
    """
    if not is_sport:
        return ""

    if relation == EvidenceRelation.TEXT_ONLY_SPORT:
        return "纯跨界（行业代码非体育，文本有体育业务）"

    if relation in (EvidenceRelation.INDIRECT_CODE_TEXT_SUPPORT,
                    EvidenceRelation.INDIRECT_CODE_TEXT_WEAK):
        return "潜在跨界（间接行业代码，文本有体育业务）"

    if relation == EvidenceRelation.DIRECT_CODE_TEXT_SUPPORT:
        non_sport_count = total_lines - sport_lines_count
        if non_sport_count > 0:
            return f"多元经营（体育+{non_sport_count}条非体育业务）"

    return ""


def derive_confidence(relation: EvidenceRelation, sport_score: float) -> float:
    """
    从 EvidenceRelation + SportScore 派生 confidence。

    Returns:
        confidence [0, 1]
    """
    if relation == EvidenceRelation.DIRECT_CODE_TEXT_SUPPORT:
        if sport_score >= 0.3:
            return 0.95
        return 0.85

    if relation == EvidenceRelation.DIRECT_CODE_TEXT_WEAK:
        return 0.55

    if relation == EvidenceRelation.DIRECT_CODE_TEXT_CONFLICT:
        return 0.55

    if relation == EvidenceRelation.INDIRECT_CODE_TEXT_SUPPORT:
        if sport_score >= 0.5:
            return 0.90
        elif sport_score >= 0.2:
            return 0.75
        return 0.60

    if relation == EvidenceRelation.TEXT_ONLY_SPORT:
        if sport_score >= 0.5:
            return 0.90
        elif sport_score >= 0.2:
            return 0.75
        return 0.60

    if relation == EvidenceRelation.INDIRECT_CODE_TEXT_WEAK:
        return 0.0

    # NO_SPORT_EVIDENCE / INSUFFICIENT_INFORMATION
    return 0.0


def is_sport_candidate(
    sport_score: float,
    relation: EvidenceRelation,
    code_type: str,
    primary_category: str = "",
) -> bool:
    """
    统一候选企业判断 — 整个项目只在这一个地方判断 is_sport。

    所有 Router、批处理、图表模块应统一从这里获得判断结果。

    Args:
        sport_score:       SportScore [0, 1]
        relation:          EvidenceRelation 枚举
        code_type:         代码类型
        primary_category:  主要体育业态分类

    Returns:
        是否为体育相关候选企业
    """
    if sport_score >= 0.10 and primary_category:
        return True
    return code_type == "direct"
