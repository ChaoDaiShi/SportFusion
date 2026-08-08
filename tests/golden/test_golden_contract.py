import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "expected_formal_metrics.json"


@pytest.fixture(scope="module")
def expected():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_boundary_set_arithmetic_distinguishes_951_934_and_977(expected):
    boundary = expected["boundary"]
    assert boundary["intersection"] + boundary["only_fusion"] == boundary["fusion_count"]
    assert boundary["intersection"] + boundary["only_traditional"] == boundary["traditional_count"]
    assert boundary["fusion_count"] - boundary["traditional_count"] == boundary["net_increase"]
    assert len({boundary["only_fusion"], boundary["net_increase"], boundary["crossover_count"]}) == 3
    assert boundary["net_increase_rate"] == pytest.approx(
        boundary["net_increase"] / boundary["traditional_count"], abs=1e-4
    )


def test_evidence_and_sportshare_sources_cover_all_candidates(expected):
    assert sum(expected["evidence_groups"].values()) == expected["boundary"]["fusion_count"]
    assert sum(expected["sportshare_sources"].values()) == expected["boundary"]["fusion_count"]


def test_reference_label_denominators_are_explicit(expected):
    labels = expected["validation"]["reference_labels"]
    assert labels["sport"] + labels["non_sport"] + labels["insufficient"] == labels["total"]
    assert labels["sport"] + labels["non_sport"] == expected["validation"]["binary_evaluable"]


def test_scale_totals_and_scenario_bounds_are_consistent(expected):
    scale = expected["scale"]
    total = scale["official_total_100m_cny"]
    assert sum(scale["category_scale_100m_cny"].values()) == pytest.approx(total, abs=0.02)
    assert scale["boundary_in_100m_cny"] + scale["boundary_out_100m_cny"] == pytest.approx(
        total, abs=0.02
    )
    assert scale["mapped_enterprises"] + scale["unresolved_enterprises"] == expected["boundary"][
        "fusion_count"
    ]
    assert scale["boundary_out_scenario_min_100m_cny"] < scale["boundary_out_100m_cny"]
    assert scale["boundary_out_100m_cny"] < scale["boundary_out_scenario_max_100m_cny"]


def test_review_priority_covers_candidates_and_p1_p2_rate(expected):
    priority = expected["review_priority"]
    assert sum(priority.values()) == expected["boundary"]["fusion_count"]
    assert priority["P1"] + priority["P2"] == 3857
    assert (priority["P1"] + priority["P2"]) / expected["boundary"][
        "total_enterprises"
    ] == pytest.approx(0.0503, abs=1e-4)
