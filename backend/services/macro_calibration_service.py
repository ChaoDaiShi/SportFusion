"""
宏观校准与结构分配服务 — Phase 3 closure: proper 5-layer model.

Layer 1: A_i = SportShare_i * G_i          (enterprise structural weight)
Layer 2: p_sample_k = Σ(A_i for cat k) / Σ(A_i)  (sample category structure)
Layer 3: p_hat_k = (1-α)*p_sample_k + α*p_official_k  (fused structure)
Layer 4: Y_hat_k = Y_total * p_hat_k        (category output)
Layer 5: Y_hat_rk = Y_hat_k * Q_rk / Σ_r(Q_rk)  (regional allocation)

alpha enters ONLY at Layer 3 (sample vs official prior blending).
alpha does NOT enter enterprise-level addition.

Official total (e.g. 2170.80亿元) enters ONLY at Layer 4.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@dataclass
class MacroCalibration:
    """宏观校准参数"""
    year: int = 2022
    region: str = "四川省"
    region_code: str = "510000"
    official_total_output: float = 2170.80  # 亿元
    unit: str = "亿元"
    source: str = ""
    source_version: str = ""


@lru_cache(maxsize=1)
def load_official_total() -> MacroCalibration:
    """加载官方总量约束配置"""
    path = _CONFIG_DIR / "official_totals.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    entry = data["entries"][0]
    return MacroCalibration(
        year=entry["year"],
        region=entry["region"],
        region_code=entry["region_code"],
        official_total_output=entry["official_total_output"],
        unit=entry["unit"],
        source=entry.get("source", ""),
        source_version=entry.get("source_version", ""),
    )


def load_official_category_prior() -> dict[str, float] | None:
    """
    加载官方九类业态结构先验 p_official_k。

    Returns None if formal artifact is missing.
    Formal callers must handle None → artifact_required.
    """
    path = _CONFIG_DIR / "official_category_prior.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: float(v) for k, v in data.get("prior", {}).items()}


# ---- Layer 1: Enterprise structural weight ----

def compute_structural_weight(
    effective_share: float,
    structural_factor: float = 1.0,
) -> float:
    """
    Layer 1: A_i = SportShare_i * G_i

    G_i = structural distribution factor.
    Default = 1.0 when no formal G_i artifact is available.
    This is a documented baseline, NOT a hardcoded report value.
    """
    return effective_share * structural_factor


# ---- Layer 2 & 3: Category structure fusion ----

def compute_sample_category_structure(
    category_weights: dict[str, float],
) -> dict[str, float]:
    """
    Layer 2: p_sample_k = weight for category k / total weight.
    """
    total = sum(category_weights.values())
    if total == 0:
        return {}
    return {k: v / total for k, v in category_weights.items()}


def fuse_category_structure(
    p_sample: dict[str, float],
    p_official: dict[str, float] | None,
    alpha: float = 0.20,
) -> dict[str, float]:
    """
    Layer 3: p_hat_k = (1 - α) * p_sample_k + α * p_official_k

    If p_official is None and alpha > 0:
        Returns empty dict → caller must handle artifact_required.
    """
    if alpha > 0 and p_official is None:
        return {}  # Signal: artifact_required

    if alpha == 0 or p_official is None:
        return dict(p_sample)

    all_cats = set(p_sample.keys()) | set(p_official.keys())
    result = {}
    for cat in all_cats:
        ps = p_sample.get(cat, 0.0)
        po = p_official.get(cat, 0.0)
        result[cat] = (1.0 - alpha) * ps + alpha * po
    return result


# ---- Layer 4: Category output allocation ----

def allocate_category_output(
    p_hat: dict[str, float],
    official_total: float,
) -> dict[str, float]:
    """
    Layer 4: Y_hat_k = Y_total * p_hat_k
    """
    return {k: round(official_total * v, 2) for k, v in p_hat.items()}


# ---- Layer 5: Regional allocation ----

def allocate_regional_output(
    category_output: dict[str, float],
    category_regional_weights: dict[str, dict[str, float]],
    unresolved_share: float = 0.0,
) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    """
    Layer 5: Y_hat_rk = Y_hat_k * Q_rk / Σ_r(Q_rk)

    Returns:
        (regional_outputs, unresolved_by_category)
        regional_outputs[category][region] = allocated output
        unresolved_by_category[category] = unresolved portion
    """
    regional: dict[str, dict[str, float]] = {}
    unresolved: dict[str, float] = {}

    for cat, cat_total in category_output.items():
        weights = category_regional_weights.get(cat, {})
        total_w = sum(weights.values())
        if total_w == 0:
            unresolved[cat] = cat_total
            continue

        regional[cat] = {}
        for region, w in weights.items():
            regional[cat][region] = round(cat_total * w / total_w, 2)

        if unresolved_share > 0:
            unresolved[cat] = round(cat_total * unresolved_share, 2)

    return regional, unresolved


# ---- Boundary split ----

@dataclass
class ScaleAllocationResult:
    """规模分配结果"""
    enterprise_id: str = ""
    credit_code: str = ""
    enterprise_name: str = ""
    sport_category: str = ""
    region: str = ""

    effective_share: float = 0.0
    structural_weight: float = 0.0
    category: str = ""
    code_type: str = "none"
    is_traditional_boundary: bool = False


def compute_boundary_split(
    allocations: list[ScaleAllocationResult],
    category_outputs: dict[str, float],
) -> dict[str, float]:
    """
    Compute inside/outside traditional boundary from final allocation.

    Uses category-level outputs with per-enterprise boundary tags
    to proportionally split each category.
    """
    inside = 0.0
    outside = 0.0

    for cat, cat_total in category_outputs.items():
        cat_allocs = [a for a in allocations if a.category == cat]
        inside_w = sum(a.structural_weight for a in cat_allocs if a.is_traditional_boundary)
        outside_w = sum(a.structural_weight for a in cat_allocs if not a.is_traditional_boundary)
        total_w = inside_w + outside_w
        if total_w > 0:
            inside += cat_total * inside_w / total_w
            outside += cat_total * outside_w / total_w

    total = inside + outside
    return {
        "inside_traditional_boundary_output": round(inside, 2),
        "outside_traditional_boundary_output": round(outside, 2),
        "official_total": round(total, 2),
        "inside_pct": round(inside / total * 100, 2) if total > 0 else 0.0,
        "outside_pct": round(outside / total * 100, 2) if total > 0 else 0.0,
    }


def normalize_weights(weights: list[float]) -> list[float]:
    """Normalize weights to sum to 1."""
    total = sum(weights)
    if total == 0:
        n = len(weights)
        return [1.0 / n] * n if n > 0 else []
    return [w / total for w in weights]
