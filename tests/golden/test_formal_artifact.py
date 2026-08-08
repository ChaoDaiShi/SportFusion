import csv
import json
from pathlib import Path

import pytest

from backend.core.configuration import sha256_file

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = json.loads(
    (ROOT / "tests" / "fixtures" / "expected_formal_metrics.json").read_text(encoding="utf-8")
)
ARTIFACT_ROOT = ROOT / "artifacts" / "formal" / EXPECTED["batch_number"]
REQUIRED = (
    "batch_metadata.json",
    "input_manifest.json",
    "recognition/recognition_summary.json",
    "recognition/evidence_group_summary.json",
    "sportshare/sportshare_summary.json",
    "scale/category_scale.csv",
    "scale/region_scale.csv",
    "scale/boundary_scale.json",
    "scale/scenarios.csv",
    "validation/binary_metrics.json",
    "validation/category_metrics.json",
    "validation/sportshare_cv.json",
    "audit/audit_checks.json",
    "SHA256SUMS",
)


def require_artifacts():
    missing = [relative for relative in REQUIRED if not (ARTIFACT_ROOT / relative).is_file()]
    if missing:
        pytest.skip("missing formal artifacts: " + ", ".join(missing))


def read_json(relative: str) -> dict:
    return json.loads((ARTIFACT_ROOT / relative).read_text(encoding="utf-8"))


def read_csv(relative: str) -> list[dict]:
    with (ARTIFACT_ROOT / relative).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


@pytest.mark.formal_artifact
def test_locked_formal_artifact_matches_golden_contract():
    require_artifacts()
    boundary = EXPECTED["boundary"]
    recognition = read_json("recognition/recognition_summary.json")
    evidence = read_json("recognition/evidence_group_summary.json")
    share = read_json("sportshare/sportshare_summary.json")
    scale = EXPECTED["scale"]
    boundary_scale = read_json("scale/boundary_scale.json")
    categories = read_csv("scale/category_scale.csv")
    regions = read_csv("scale/region_scale.csv")
    scenarios = read_csv("scale/scenarios.csv")
    binary = read_json("validation/binary_metrics.json")
    category = read_json("validation/category_metrics.json")
    share_cv = read_json("validation/sportshare_cv.json")
    audit = read_json("audit/audit_checks.json")

    for key in (
        "total_enterprises",
        "traditional_count",
        "fusion_count",
        "intersection",
        "only_fusion",
        "only_traditional",
        "net_increase",
        "crossover_count",
    ):
        assert recognition[key] == boundary[key]
    assert sum(evidence.values()) == boundary["fusion_count"]
    assert share["model_estimated"] == EXPECTED["sportshare_sources"]["model_estimated"]
    assert share["hierarchical_fallback"] == EXPECTED["sportshare_sources"]["hierarchical_fallback"]
    assert float(boundary_scale["boundary_in_100m_cny"]) == pytest.approx(
        scale["boundary_in_100m_cny"], abs=0.02
    )
    assert float(boundary_scale["boundary_out_100m_cny"]) == pytest.approx(
        scale["boundary_out_100m_cny"], abs=0.02
    )
    assert sum(float(row["scale_100m_cny"]) for row in categories) == pytest.approx(
        scale["official_total_100m_cny"], abs=0.02
    )
    assert sum(float(row["scale_100m_cny"]) for row in regions) == pytest.approx(
        scale["official_total_100m_cny"], abs=0.02
    )
    assert len(scenarios) == scale["scenario_count"]
    assert all(
        float(row["total_output_100m_cny"])
        == pytest.approx(scale["official_total_100m_cny"], abs=0.02)
        for row in scenarios
    )
    assert binary["f1"] == pytest.approx(EXPECTED["validation"]["binary"]["f1"], abs=1e-4)
    assert category["macro_f1"] == pytest.approx(
        EXPECTED["validation"]["category"]["macro_f1"], abs=1e-4
    )
    assert share_cv["r2"] == pytest.approx(
        EXPECTED["validation"]["sportshare"]["r2"], abs=1e-4
    )
    assert sum(item["status"] == "PASS" for item in audit["checks"]) == 24


@pytest.mark.formal_artifact
def test_sha256_manifest_covers_every_formal_file():
    require_artifacts()
    entries = {}
    for line in (ARTIFACT_ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(maxsplit=1)
        entries[relative.lstrip("* ")] = digest
    for relative in REQUIRED[:-1]:
        assert entries[relative] == sha256_file(ARTIFACT_ROOT / relative)
