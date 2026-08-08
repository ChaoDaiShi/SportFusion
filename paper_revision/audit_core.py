from __future__ import annotations

from math import fsum
from typing import Iterable


def pct(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / float(denominator) * 100, 2) if denominator else 0.0


def compute_snapshot_from_counts(
    total: int,
    traditional: int,
    fusion: int,
    crossover: int,
) -> dict:
    return {
        "total_enterprises": int(total),
        "traditional_sport_enterprises": int(traditional),
        "fusion_sport_enterprises": int(fusion),
        "crossover_enterprises": int(crossover),
        "traditional_coverage_pct": pct(traditional, total),
        "fusion_coverage_pct": pct(fusion, total),
        "incremental_enterprises": int(fusion - traditional),
        "relative_identification_increase_pct": pct(fusion - traditional, traditional),
    }


def classify_evidence(source_kind: str, reproducible: bool, conflict: bool) -> str:
    if conflict or not reproducible:
        return "D"
    return {
        "raw_data": "A",
        "derived_output": "B",
        "authority": "C",
    }.get(source_kind, "D")


def concentration_metrics(values: Iterable[int | float]) -> dict:
    positive = sorted(max(float(value), 0.0) for value in values)
    total = fsum(positive)
    if total <= 0:
        return {"cr3_pct": 0.0, "cr5_pct": 0.0, "hhi": 0.0, "gini": 0.0}

    descending = list(reversed(positive))
    shares = [value / total for value in positive]
    n = len(positive)
    absolute_differences = fsum(abs(left - right) for left in positive for right in positive)
    return {
        "cr3_pct": round(fsum(descending[:3]) / total * 100, 2),
        "cr5_pct": round(fsum(descending[:5]) / total * 100, 2),
        "hhi": round(fsum(share * share for share in shares) * 10000, 2),
        "gini": round(absolute_differences / (2 * n * total), 6),
    }
