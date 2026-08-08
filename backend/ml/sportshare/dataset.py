"""
SportShare dataset construction.

Target T_i = sport_business_lines / effective_business_lines (structural ratio).
NOT revenue share — a structural descriptor of the business scope composition.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SportShareSample:
    """Single training/inference sample for SportShare."""

    enterprise_id: str | None = None
    credit_code: str | None = None
    features: list[float] = field(default_factory=list)
    target: float | None = None  # T_i structural target
    sport_score: float = 0.0
    code_type: str = "none"
    sport_category: str = ""
    total_lines: int = 0
    sport_lines: int = 0


def build_target(business_text: str) -> float | None:
    """
    Build structural target T_i = sport_business_lines / total_business_lines.

    Returns None if text is empty (cannot compute target).
    """
    from services.business_line_service import classify_business_line, parse_business_lines

    if not business_text or len(business_text.strip()) < 2:
        return None

    lines = parse_business_lines(business_text)
    if not lines:
        return None

    classified = [classify_business_line(line) for line in lines]
    sport_count = sum(1 for c in classified if c["is_sport"])
    return sport_count / len(lines)


def build_training_samples(
    enterprises: list[dict[str, Any]],
    recognition_results: list[dict[str, Any]] | None = None,
) -> list[SportShareSample]:
    """
    Build training samples from enterprise data and (optional) recognition results.

    Each sample includes:
        - Leakage-safe features (via build_sportshare_features)
        - Structural target T_i (via build_target)
        - Metadata for traceability
    """
    from ml.sportshare.features import build_sportshare_features, sportshare_features_to_array

    samples = []
    for i, ent in enumerate(enterprises):
        text = ent.get("business_text", ent.get("主要业务活动", ""))
        code = ent.get("industry_code", ent.get("行业代码"))

        # sport_score is NOT used as a feature (indirect T_i leakage via W1)
        target = build_target(text)

        fv = build_sportshare_features(
            business_text=text,
            industry_code=code,
        )

        sample = SportShareSample(
            enterprise_id=str(ent.get("enterprise_id", ent.get("credit_code", i))),
            credit_code=ent.get("credit_code", ent.get("统一社会信用代码", "")),
            features=sportshare_features_to_array(fv),
            target=target,
            sport_score=0.0,  # metadata only, NOT a feature
            code_type=fv.code_type,
            sport_category=fv.primary_sport_category,
            total_lines=fv.business_line_count,
            sport_lines=fv.sport_term_count,
        )

        # Only include samples with valid targets
        if target is not None:
            samples.append(sample)

    return samples


def get_feature_matrix(samples: list[SportShareSample]) -> list[list[float]]:
    """Extract feature matrix X from samples."""
    return [s.features for s in samples]


def get_target_vector(samples: list[SportShareSample]) -> list[float]:
    """Extract target vector y from samples."""
    return [s.target for s in samples if s.target is not None]
