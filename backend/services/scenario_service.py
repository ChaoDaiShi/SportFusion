"""
情景分析引擎 — 3种证据校准 × 4种结构先验 = 12 scenarios

3 evidence calibrations × 4 structural priors (alpha ∈ {0, 0.10, 0.20, 0.30})

Baseline: alpha = 0.20 with standard evidence calibration.
"""

from dataclasses import dataclass, field
from typing import Any

# 证据校准模式
EVIDENCE_CALIBRATIONS = ["standard", "conservative", "aggressive"]

# 结构先验参数
STRUCTURAL_PRIORS = [0.0, 0.10, 0.20, 0.30]

BASELINE_ALPHA = 0.20


@dataclass
class ScenarioConfig:
    """单个情景配置"""
    scenario_id: str
    evidence_calibration: str
    alpha: float
    description: str = ""


@dataclass
class ScenarioResult:
    """单个情景运行结果"""
    scenario_id: str = ""
    evidence_calibration: str = ""
    alpha: float = 0.0
    total_allocated: float = 0.0
    category_outputs: dict[str, float] = field(default_factory=dict)
    region_outputs: dict[str, float] = field(default_factory=dict)
    boundary_outputs: dict[str, float] = field(default_factory=dict)
    summary_metrics: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, str] = field(default_factory=dict)


def generate_scenario_configs() -> list[ScenarioConfig]:
    """生成全部12个情景配置"""
    configs = []
    for cal in EVIDENCE_CALIBRATIONS:
        for alpha in STRUCTURAL_PRIORS:
            sid = f"{cal}_alpha_{int(alpha*100):02d}"
            desc = f"证据校准={cal}, 结构先验α={alpha:.2f}"
            configs.append(ScenarioConfig(
                scenario_id=sid,
                evidence_calibration=cal,
                alpha=alpha,
                description=desc,
            ))
    return configs


def apply_evidence_calibration(
    sport_scores: list[float],
    mode: str = "standard",
) -> list[float]:
    """
    应用证据校准变换。

    standard:    不变
    conservative: sqrt(s) — 压缩高值，需要更强证据
    aggressive:   s^2 — 放大差异，更激进识别
    """
    if mode == "standard":
        return sport_scores
    elif mode == "conservative":
        return [s ** 0.5 for s in sport_scores]
    elif mode == "aggressive":
        return [s ** 2 for s in sport_scores]
    else:
        return sport_scores


def run_scenario(
    config: ScenarioConfig,
    enterprises: list[dict[str, Any]],
    sportshare_estimates: list[Any],
    recognition_results: list[dict[str, Any]],
) -> ScenarioResult:
    """运行单个情景"""
    from services.macro_calibration_service import (
        allocate_output,
        compute_boundary_split,
        compute_enterprise_weight,
        load_official_total,
        normalize_weights,
    )

    calibration = load_official_total()
    official_total = calibration.official_total_output

    # 提取 sport_scores 并应用校准
    sport_scores = [r.get("sport_score", 0.0) if r else 0.0 for r in recognition_results]
    calibrated_scores = apply_evidence_calibration(sport_scores, config.evidence_calibration)

    # 计算权重
    raw_weights = []
    for i, ent in enumerate(enterprises):
        est = sportshare_estimates[i] if i < len(sportshare_estimates) else None
        es = est.effective_share if est else 0.0
        w = compute_enterprise_weight(es, calibrated_scores[i], "none", config.alpha)
        raw_weights.append(w)

    norm_weights = normalize_weights(raw_weights)
    outputs = allocate_output(official_total, norm_weights)

    # 分类汇总
    from services.macro_calibration_service import ScaleAllocationResult

    allocations = []
    for i, ent in enumerate(enterprises):
        rec = recognition_results[i] if i < len(recognition_results) else None
        allocations.append(ScaleAllocationResult(
            enterprise_id=str(i),
            sport_category=rec.get("sport_category", "") if rec else "",
            effective_share=sportshare_estimates[i].effective_share if i < len(sportshare_estimates) else 0.0,
            sport_score=calibrated_scores[i],
            weight=raw_weights[i],
            normalized_weight=norm_weights[i],
            allocated_output=outputs[i],
            code_type=rec.get("code_type", "none") if rec else "none",
            is_traditional_boundary=(rec.get("code_type") == "direct" if rec else False),
        ))

    # 业态汇总
    cat_outputs: dict[str, float] = {}
    for a in allocations:
        cat = a.sport_category or "未分类"
        cat_outputs[cat] = cat_outputs.get(cat, 0.0) + a.allocated_output

    # 边界
    boundary = compute_boundary_split(allocations)

    return ScenarioResult(
        scenario_id=config.scenario_id,
        evidence_calibration=config.evidence_calibration,
        alpha=config.alpha,
        total_allocated=round(sum(outputs), 2),
        category_outputs={k: round(v, 2) for k, v in cat_outputs.items()},
        boundary_outputs=boundary,
        summary_metrics={
            "n_enterprises": len(enterprises),
            "official_total": official_total,
        },
        provenance={
            "scenario_version": "SCENARIO-2026-08",
            "calibration_version": calibration.source_version,
        },
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
