"""
宏观校准服务 — 使用官方区域体育产业总量约束进行结构分配。

核心原则：
    2170.80亿元是宏观校准约束，只能进入规模分配阶段。
    不进入 SportScore 或 SportShare 训练。

方法：
    enterprise_weight_i = f(SportShare, structural_evidence)
    normalized_weight_i = weight_i / Σ weight_i
    allocated_output_i = official_total × normalized_weight_i
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

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
    entry = data["entries"][0]  # Use first enabled entry
    return MacroCalibration(
        year=entry["year"],
        region=entry["region"],
        region_code=entry["region_code"],
        official_total_output=entry["official_total_output"],
        unit=entry["unit"],
        source=entry.get("source", ""),
        source_version=entry.get("source_version", ""),
    )


def compute_enterprise_weight(
    effective_share: float,
    sport_score: float,
    code_type: str = "none",
    alpha: float = 0.20,
) -> float:
    """
    计算企业在总量分配中的结构权重。

    weight = effective_share + alpha × sport_score

    alpha 控制 SportScore 结构先验的影响程度。
    alpha = 0.20 为正式基准。

    Args:
        effective_share: SportShare effective_share
        sport_score: SportScore (体育业务证据评分)
        code_type: 行业代码类型
        alpha: 结构先验参数 [0, 1]

    Returns:
        企业权重（非归一化）
    """
    return effective_share + alpha * sport_score


def normalize_weights(weights: list[float]) -> list[float]:
    """
    归一化权重使 Σ w_i = 1。

    如果所有权重为0，返回均匀权重。
    """
    total = sum(weights)
    if total == 0:
        n = len(weights)
        return [1.0 / n] * n if n > 0 else []
    return [w / total for w in weights]


def allocate_output(
    official_total: float,
    weights: list[float],
) -> list[float]:
    """
    根据归一化权重分配官方总量。

    Args:
        official_total: 官方总量（亿元）
        weights: 归一化权重（Σ = 1）

    Returns:
        每家企业的分配产出（亿元）
    """
    return [official_total * w for w in weights]


@dataclass
class ScaleAllocationResult:
    """规模分配结果"""

    enterprise_id: str = ""
    credit_code: str = ""
    enterprise_name: str = ""
    sport_category: str = ""
    region: str = ""
    region_code: str = ""

    effective_share: float = 0.0
    sport_score: float = 0.0
    weight: float = 0.0
    normalized_weight: float = 0.0
    allocated_output: float = 0.0  # 亿元

    share_source: str = "none"
    code_type: str = "none"
    is_traditional_boundary: bool = False


def run_scale_allocation(
    enterprises: list[dict[str, Any]],
    sportshare_estimates: list[Any],
    recognition_results: list[dict[str, Any]] | None = None,
    alpha: float = 0.20,
) -> list[ScaleAllocationResult]:
    """
    执行完整的规模分配 pipeline。

    1. 计算每家企业权重
    2. 归一化
    3. 用官方总量分配
    4. 标记传统边界内外
    """
    calibration = load_official_total()
    official_total = calibration.official_total_output

    # 计算权重
    raw_weights = []
    for i, ent in enumerate(enterprises):
        est = sportshare_estimates[i] if i < len(sportshare_estimates) else None
        rec = recognition_results[i] if recognition_results and i < len(recognition_results) else None

        es = est.effective_share if est else 0.0
        ss = rec.get("sport_score", 0.0) if rec else 0.0
        ct = rec.get("code_type", "none") if rec else "none"

        w = compute_enterprise_weight(es, ss, ct, alpha)
        raw_weights.append(w)

    # 归一化
    norm_weights = normalize_weights(raw_weights)

    # 分配
    outputs = allocate_output(official_total, norm_weights)

    # 构建结果
    results = []
    for i, ent in enumerate(enterprises):
        est = sportshare_estimates[i] if i < len(sportshare_estimates) else None
        rec = recognition_results[i] if recognition_results and i < len(recognition_results) else None

        result = ScaleAllocationResult(
            enterprise_id=str(ent.get("enterprise_id", ent.get("credit_code", i))),
            credit_code=ent.get("credit_code", ""),
            enterprise_name=ent.get("enterprise_name", ent.get("name", "")),
            sport_category=rec.get("sport_category", "") if rec else "",
            region=ent.get("region", ""),
            region_code=ent.get("region_code", ""),
            effective_share=est.effective_share if est else 0.0,
            sport_score=rec.get("sport_score", 0.0) if rec else 0.0,
            weight=raw_weights[i],
            normalized_weight=norm_weights[i],
            allocated_output=outputs[i],
            share_source=est.share_source if est else "none",
            code_type=rec.get("code_type", "none") if rec else "none",
            is_traditional_boundary=(rec.get("code_type") == "direct" if rec else False),
        )
        results.append(result)

    return results


def compute_boundary_split(
    allocations: list[ScaleAllocationResult],
) -> dict[str, float]:
    """
    计算传统代码边界内外规模。

    Returns:
        {
            "inside_traditional_boundary_output": float,
            "outside_traditional_boundary_output": float,
            "official_total": float,
        }
    """
    inside = sum(a.allocated_output for a in allocations if a.is_traditional_boundary)
    outside = sum(a.allocated_output for a in allocations if not a.is_traditional_boundary)
    total = sum(a.allocated_output for a in allocations)

    return {
        "inside_traditional_boundary_output": round(inside, 2),
        "outside_traditional_boundary_output": round(outside, 2),
        "official_total": round(total, 2),
        "inside_pct": round(inside / total * 100, 2) if total > 0 else 0.0,
        "outside_pct": round(outside / total * 100, 2) if total > 0 else 0.0,
    }
