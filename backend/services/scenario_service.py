"""
情景分析引擎 — Phase 3 closure: 3 evidence calibrations × 4 structural priors = 12

Evidence calibration: affects evidence/micro weight rules ONLY.
Alpha: affects ONLY Layer 3 (sample vs official category prior blending).

alpha does NOT enter enterprise-level weight formula.
Enterprise SportShare and SportScore are invariant to alpha.
"""

from dataclasses import dataclass, field
from typing import Any

from services.macro_calibration_service import (
    ScaleAllocationResult,
    allocate_category_output,
    compute_boundary_split,
    compute_sample_category_structure,
    compute_structural_weight,
    fuse_category_structure,
    load_official_category_prior,
    load_official_total,
)

EVIDENCE_CALIBRATIONS = ["standard", "conservative", "aggressive"]
STRUCTURAL_PRIORS = [0.0, 0.10, 0.20, 0.30]
BASELINE_ALPHA = 0.20


@dataclass
class ScenarioConfig:
    scenario_id: str
    evidence_calibration: str
    alpha: float
    description: str = ""


@dataclass
class ScenarioResult:
    scenario_id: str = ""
    evidence_calibration: str = ""
    alpha: float = 0.0
    total_allocated: float = 0.0
    category_outputs: dict[str, float] = field(default_factory=dict)
    region_outputs: dict[str, dict[str, float]] = field(default_factory=dict)
    boundary_outputs: dict[str, float] = field(default_factory=dict)
    summary_metrics: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, str] = field(default_factory=dict)
    status: str = "ok"  # "ok" | "artifact_required"


def generate_scenario_configs() -> list[ScenarioConfig]:
    configs = []
    for cal in EVIDENCE_CALIBRATIONS:
        for alpha in STRUCTURAL_PRIORS:
            sid = f"{cal}_alpha_{int(alpha*100):02d}"
            configs.append(ScenarioConfig(
                scenario_id=sid,
                evidence_calibration=cal,
                alpha=alpha,
                description=f"证据校准={cal}, 结构先验α={alpha:.2f}",
            ))
    return configs


def apply_evidence_calibration(
    structural_weights: list[float],
    mode: str = "standard",
) -> list[float]:
    """
    Apply evidence calibration to structural weights.

    standard:     unchanged
    conservative: sqrt(w) — compresses high values
    aggressive:   w^2 — amplifies differences
    """
    if mode == "standard":
        return structural_weights
    elif mode == "conservative":
        return [w ** 0.5 for w in structural_weights]
    elif mode == "aggressive":
        return [w ** 2 for w in structural_weights]
    return structural_weights


def run_scenario(
    config: ScenarioConfig,
    enterprises: list[dict[str, Any]],
    sportshare_estimates: list[Any],
    recognition_results: list[dict[str, Any]],
) -> ScenarioResult:
    """
    Run a single scenario through the 5-layer allocation model.

    Layer 1: A_i = SportShare_i * G_i
    Layer 2: p_sample_k
    Layer 3: p_hat_k = (1-α)*p_sample_k + α*p_official_k
    Layer 4: Y_hat_k = Y_total * p_hat_k
    Layer 5: Y_hat_rk
    """
    calibration = load_official_total()
    official_total = calibration.official_total_output

    # ---- Layer 1: enterprise structural weights ----
    raw_weights = []
    for i, ent in enumerate(enterprises):
        est = sportshare_estimates[i] if i < len(sportshare_estimates) else None
        es = est.effective_share if est else 0.0
        w = compute_structural_weight(es, structural_factor=1.0)
        raw_weights.append(w)

    # Evidence calibration affects Layer 1 weights
    calibrated_weights = apply_evidence_calibration(raw_weights, config.evidence_calibration)

    # ---- Layer 2: sample category structure ----
    cat_weights: dict[str, float] = {}
    allocations = []
    for i, ent in enumerate(enterprises):
        rec = recognition_results[i] if i < len(recognition_results) else None
        est = sportshare_estimates[i] if i < len(sportshare_estimates) else None
        cat = rec.get("sport_category", "未分类") if rec else "未分类"
        ct = rec.get("code_type", "none") if rec else "none"

        cat_weights[cat] = cat_weights.get(cat, 0.0) + calibrated_weights[i]
        allocations.append(ScaleAllocationResult(
            enterprise_id=str(i),
            sport_category=cat,
            effective_share=est.effective_share if est else 0.0,
            structural_weight=calibrated_weights[i],
            category=cat,
            code_type=ct,
            is_traditional_boundary=(ct == "direct"),
        ))

    p_sample = compute_sample_category_structure(cat_weights)

    # ---- Layer 3: fuse with official prior (alpha enters HERE) ----
    p_official = load_official_category_prior()
    p_hat = fuse_category_structure(p_sample, p_official, config.alpha)

    if not p_hat and config.alpha > 0:
        # Formal artifact missing — cannot use alpha > 0
        return ScenarioResult(
            scenario_id=config.scenario_id,
            evidence_calibration=config.evidence_calibration,
            alpha=config.alpha,
            status="artifact_required",
            provenance={
                "scenario_version": "SCENARIO-2026-08",
                "reason": "official_category_prior.json not found",
            },
        )

    # ---- Layer 4: category output ----
    cat_outputs = allocate_category_output(p_hat, official_total)

    # ---- Layer 5: regional allocation (placeholder — no region data) ----
    regional_outputs: dict[str, dict[str, float]] = {}

    # ---- Boundary split ----
    boundary = compute_boundary_split(allocations, cat_outputs)

    return ScenarioResult(
        scenario_id=config.scenario_id,
        evidence_calibration=config.evidence_calibration,
        alpha=config.alpha,
        total_allocated=round(sum(cat_outputs.values()), 2),
        category_outputs=cat_outputs,
        region_outputs=regional_outputs,
        boundary_outputs=boundary,
        summary_metrics={
            "n_enterprises": len(enterprises),
            "official_total": official_total,
        },
        provenance={
            "scenario_version": "SCENARIO-2026-08",
            "calibration_version": calibration.source_version,
        },
        status="ok",
    )


def run_all_scenarios(
    enterprises: list[dict[str, Any]],
    sportshare_estimates: list[Any],
    recognition_results: list[dict[str, Any]],
) -> list[ScenarioResult]:
    """批量运行全部12个情景"""
    configs = generate_scenario_configs()
    results = []
    for config in configs:
        result = run_scenario(config, enterprises, sportshare_estimates, recognition_results)
        results.append(result)
    return results
