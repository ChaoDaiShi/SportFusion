import csv
import hashlib
import json
from pathlib import Path

import pytest

EXPECTED_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "expected_formal_metrics.json"


def _write_json(root: Path, relative: str, payload: object) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(root: Path, relative: str, rows: list[dict[str, object]]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refresh_sha256sums(root: Path) -> None:
    paths = sorted(
        path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS"
    )
    lines = [f"{_sha256(path)}  {path.relative_to(root).as_posix()}" for path in paths]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _synthetic_region_rows(scale: dict) -> list[dict[str, object]]:
    """Build tmp-only values satisfying the source-locked 21-row/CR5 invariants."""
    total = scale["official_total_100m_cny"]
    values = [
        scale["chengdu_100m_cny"],
        85.83,
        85.83,
        85.83,
        85.82,
        *([37.62] * 15),
        37.66,
    ]
    return [
        {
            "region": "成都市" if index == 1 else f"SYNTHETIC-REGION-{index:02d}",
            "scale_100m_cny": value,
            "share": scale["chengdu_share"] if index == 1 else value / total,
            "mapping_status": "mapped",
        }
        for index, value in enumerate(values, start=1)
    ]


def _build_valid_artifact(root: Path, expected: dict) -> Path:
    root.mkdir(parents=True)
    batch_number = expected["batch_number"]
    scale = expected["scale"]
    input_digest = "d" * 64

    _write_json(
        root,
        "batch_metadata.json",
        {
            "batch_number": batch_number,
            "mode": "formal",
            "data_version": "DATA-20260803-R1",
            "model_version": "SPORTSCORE-20260803-R1",
            "feature_version": "FEATURE-20260803-R1",
            "dictionary_version": "DICTIONARY-20260803-R1",
            "dictionary_sha256": "a" * 64,
            "code_map_version": "CODE-MAP-20260803-R1",
            "code_map_sha256": "b" * 64,
            "sportshare_model_id": "SPORTSHARE-RF-20260803-R1",
            "sportshare_model_sha256": "c" * 64,
            "evidence_calibration_version": "EVIDENCE-CALIBRATION-20260803-R1",
            "scale_config_version": "SCALE-SCENARIO-20260803-R1",
            "candidate_threshold": 0.10,
            "alpha": scale["baseline_alpha"],
            "official_total_id": "SC-SPORT-2022",
            "official_total_100m_cny": scale["official_total_100m_cny"],
            "input_file_sha256": input_digest,
            "start_time": "2026-08-03T11:00:00+08:00",
            "end_time": "2026-08-03T12:00:00+08:00",
            "runtime_env_json": {"runtime_id": "synthetic-offline-test"},
            "status": "formal-completed",
            "locked_at": "2026-08-03T12:00:00+08:00",
        },
    )
    _write_json(
        root,
        "input_manifest.json",
        {
            "batch_number": batch_number,
            "mode": "formal",
            "source_mode": "formal",
            "input_file_sha256": input_digest,
            "inputs": [
                {
                    "path": "restricted-inputs/sportfusion-enterprises.csv",
                    "sha256": input_digest,
                    "provenance": "formal",
                }
            ],
        },
    )
    _write_json(
        root,
        "recognition/recognition_summary.json",
        {**expected["boundary"], "review_priority": expected["review_priority"]},
    )
    _write_json(root, "recognition/evidence_group_summary.json", expected["evidence_groups"])
    _write_json(
        root,
        "sportshare/sportshare_summary.json",
        {
            "sources": expected["sportshare_sources"],
            "total_share_results": expected["boundary"]["fusion_count"],
        },
    )
    _write_csv(
        root,
        "scale/category_scale.csv",
        [
            {"category": category, "scale_100m_cny": value}
            for category, value in scale["category_scale_100m_cny"].items()
        ],
    )
    _write_csv(
        root,
        "scale/region_scale.csv",
        _synthetic_region_rows(scale),
    )
    _write_json(
        root,
        "scale/boundary_scale.json",
        {
            "official_total_100m_cny": scale["official_total_100m_cny"],
            "alpha": scale["baseline_alpha"],
            "boundary_in_100m_cny": scale["boundary_in_100m_cny"],
            "boundary_out_100m_cny": scale["boundary_out_100m_cny"],
            "boundary_out_share": scale["boundary_out_share"],
            "mapped_enterprises": scale["mapped_enterprises"],
            "unresolved_enterprises": scale["unresolved_enterprises"],
        },
    )

    scenario_rows = []
    for profile_index, profile in enumerate(("conservative", "baseline", "expanded")):
        for alpha_index, alpha_token in enumerate(("0.00", "0.10", "0.20", "0.30")):
            boundary_out = scale["boundary_out_100m_cny"]
            if profile_index == 0 and alpha_index == 0:
                boundary_out = scale["boundary_out_scenario_min_100m_cny"]
            elif profile_index == 2 and alpha_index == 3:
                boundary_out = scale["boundary_out_scenario_max_100m_cny"]
            scenario_rows.append(
                {
                    "scenario_id": f"{profile}-alpha-{alpha_token}",
                    "evidence_profile": profile,
                    "alpha": alpha_token,
                    "total_output_100m_cny": scale["official_total_100m_cny"],
                    "boundary_in_100m_cny": scale["official_total_100m_cny"] - boundary_out,
                    "boundary_out_100m_cny": boundary_out,
                }
            )
    _write_csv(root, "scale/scenarios.csv", scenario_rows)

    validation = expected["validation"]
    _write_json(
        root,
        "validation/binary_metrics.json",
        {
            **validation["binary"],
            "binary_evaluable": validation["binary_evaluable"],
            "reference_labels": validation["reference_labels"],
        },
    )
    _write_json(
        root,
        "validation/category_metrics.json",
        {
            **validation["category"],
            "category_evaluable": validation["category_evaluable"],
        },
    )
    _write_json(root, "validation/sportshare_cv.json", validation["sportshare"])
    _write_json(
        root,
        "audit/audit_checks.json",
        {
            "pass_count": validation["audit"]["passed"],
            "total": validation["audit"]["total"],
            "checks": [
                {
                    "check_id": f"AUD-{index:02d}",
                    "name": f"synthetic_check_{index:02d}",
                    "status": "PASS",
                    "expected": True,
                    "actual": True,
                    "detail": "synthetic contract fixture",
                }
                for index in range(1, 25)
            ],
        },
    )

    extra = root / "audit" / "raw" / "runtime.txt"
    extra.parent.mkdir(parents=True)
    extra.write_text("synthetic runtime evidence\n", encoding="utf-8")
    _refresh_sha256sums(root)
    return root


def _read_json(root: Path, relative: str) -> dict:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _read_csv(root: Path, relative: str) -> list[dict[str, str]]:
    with (root / relative).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_valid_synthetic_artifact_passes(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)

    validate_formal_artifact(artifact_root, expected)


def test_synthetic_artifact_contains_the_fixture_review_priority(tmp_path):
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)

    recognition = _read_json(artifact_root, "recognition/recognition_summary.json")

    assert recognition["review_priority"] == expected["review_priority"]


@pytest.mark.parametrize("mutation", ["missing-group", "missing-key", "extra-key", "same-total"])
def test_review_priority_requires_the_exact_fixture_distribution(tmp_path, mutation):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    recognition = _read_json(artifact_root, "recognition/recognition_summary.json")
    if mutation == "missing-group":
        recognition.pop("review_priority")
    else:
        priority = recognition["review_priority"]
        if mutation == "missing-key":
            priority.pop("P4")
        elif mutation == "extra-key":
            priority["P5"] = 0
        else:
            priority["P1"] -= 1
            priority["P2"] += 1
    _write_json(artifact_root, "recognition/recognition_summary.json", recognition)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="review priority"):
        validate_formal_artifact(artifact_root, expected)


def test_rejects_legacy_input_provenance_even_with_recomputed_hashes(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    manifest = _read_json(artifact_root, "input_manifest.json")
    manifest["inputs"][0]["path"] = (
        "data/processed_BATCH-20260803-R1/enterprise_recognition_results.csv"
    )
    _write_json(artifact_root, "input_manifest.json", manifest)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="legacy"):
        validate_formal_artifact(artifact_root, expected)


def test_rejects_wrong_evidence_distribution_with_the_same_sum(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    evidence = _read_json(artifact_root, "recognition/evidence_group_summary.json")
    evidence["code_text_consistent"] -= 1
    evidence["code_only"] += 1
    _write_json(artifact_root, "recognition/evidence_group_summary.json", evidence)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="evidence"):
        validate_formal_artifact(artifact_root, expected)


def test_rejects_wrong_locked_metric_even_with_a_valid_hash(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    recognition = _read_json(artifact_root, "recognition/recognition_summary.json")
    recognition["candidate_coverage_rate"] += 0.01
    _write_json(artifact_root, "recognition/recognition_summary.json", recognition)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="recognition"):
        validate_formal_artifact(artifact_root, expected)


def test_rejects_an_extra_failed_audit_check(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    audit = _read_json(artifact_root, "audit/audit_checks.json")
    audit["checks"].append(
        {
            "check_id": "AUD-EXTRA",
            "name": "extra_failure",
            "status": "FAIL",
            "expected": True,
            "actual": False,
            "detail": "must invalidate formal-completed",
        }
    )
    _write_json(artifact_root, "audit/audit_checks.json", audit)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="audit"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate", "hash-mismatch"])
def test_rejects_invalid_sha256sum_entries(tmp_path, mutation):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    manifest_path = artifact_root / "SHA256SUMS"
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    if mutation == "missing":
        lines.pop(0)
    elif mutation == "extra":
        lines.append(f"{'e' * 64}  does-not-exist.txt")
    elif mutation == "duplicate":
        lines.append(lines[0])
    else:
        _digest, relative = lines[0].split(maxsplit=1)
        lines[0] = f"{'f' * 64}  {relative}"
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="SHA256SUMS"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("batch_number", "BATCH-WRONG"),
        ("mode", "demo"),
        ("status", "locked"),
        ("locked_at", ""),
        ("start_time", ""),
        ("end_time", ""),
        ("runtime_env_json", {}),
        ("data_version", ""),
        ("data_version", True),
        ("model_version", "legacy-model"),
        ("feature_version", "demo-feature"),
        ("dictionary_version", "NOT-IMPORTED"),
        ("code_map_version", "test-map"),
        ("sportshare_model_id", "legacy-rf"),
        ("evidence_calibration_version", "demo-calibration"),
        ("scale_config_version", "test-scale"),
        ("dictionary_sha256", "not-a-sha256"),
        ("code_map_sha256", "b" * 63),
        ("sportshare_model_sha256", "G" * 64),
        ("input_file_sha256", "d" * 63),
        ("candidate_threshold", None),
        ("alpha", 0.30),
        ("official_total_id", ""),
        ("official_total_100m_cny", 1.0),
    ],
)
def test_rejects_invalid_or_legacy_batch_metadata(tmp_path, field, invalid_value):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    metadata = _read_json(artifact_root, "batch_metadata.json")
    metadata[field] = invalid_value
    _write_json(artifact_root, "batch_metadata.json", metadata)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="batch_metadata"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("batch_number", "BATCH-WRONG"),
        ("mode", "demo"),
        ("source_mode", "legacy"),
        ("input_file_sha256", "e" * 64),
        ("inputs", []),
    ],
)
def test_rejects_input_manifest_not_bound_to_formal_batch(tmp_path, field, invalid_value):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    manifest = _read_json(artifact_root, "input_manifest.json")
    manifest[field] = invalid_value
    _write_json(artifact_root, "input_manifest.json", manifest)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="input_manifest"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [("path", ""), ("sha256", "bad-hash"), ("provenance", "")],
)
def test_rejects_incomplete_declared_input_provenance(tmp_path, field, invalid_value):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    manifest = _read_json(artifact_root, "input_manifest.json")
    manifest["inputs"][0][field] = invalid_value
    _write_json(artifact_root, "input_manifest.json", manifest)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="input_manifest"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    "metric_case",
    [
        "sportshare-source",
        "category-scale",
        "boundary-scale",
        "region-scale",
        "scenario-baseline",
        "binary-metric",
        "category-metric",
        "sportshare-metric",
        "binary-denominator",
        "reference-labels",
    ],
)
def test_rejects_mutation_of_each_locked_metric_group(tmp_path, metric_case):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)

    if metric_case == "sportshare-source":
        payload = _read_json(artifact_root, "sportshare/sportshare_summary.json")
        payload["sources"]["model_estimated"] += 1
        _write_json(artifact_root, "sportshare/sportshare_summary.json", payload)
    elif metric_case == "category-scale":
        rows = _read_csv(artifact_root, "scale/category_scale.csv")
        rows[0]["scale_100m_cny"] = str(float(rows[0]["scale_100m_cny"]) + 1)
        rows[1]["scale_100m_cny"] = str(float(rows[1]["scale_100m_cny"]) - 1)
        _write_csv(artifact_root, "scale/category_scale.csv", rows)
    elif metric_case == "boundary-scale":
        payload = _read_json(artifact_root, "scale/boundary_scale.json")
        payload["boundary_out_share"] += 0.01
        _write_json(artifact_root, "scale/boundary_scale.json", payload)
    elif metric_case == "region-scale":
        rows = _read_csv(artifact_root, "scale/region_scale.csv")
        rows[0]["share"] = str(float(rows[0]["share"]) + 0.01)
        _write_csv(artifact_root, "scale/region_scale.csv", rows)
    elif metric_case == "scenario-baseline":
        rows = _read_csv(artifact_root, "scale/scenarios.csv")
        baseline = next(
            row
            for row in rows
            if row["evidence_profile"] == "baseline" and float(row["alpha"]) == 0.20
        )
        baseline["boundary_out_100m_cny"] = "200.0"
        _write_csv(artifact_root, "scale/scenarios.csv", rows)
    elif metric_case == "binary-metric":
        payload = _read_json(artifact_root, "validation/binary_metrics.json")
        payload["precision"] += 0.01
        _write_json(artifact_root, "validation/binary_metrics.json", payload)
    elif metric_case == "category-metric":
        payload = _read_json(artifact_root, "validation/category_metrics.json")
        payload["macro_f1"] += 0.01
        _write_json(artifact_root, "validation/category_metrics.json", payload)
    elif metric_case == "sportshare-metric":
        payload = _read_json(artifact_root, "validation/sportshare_cv.json")
        payload["spearman"] += 0.01
        _write_json(artifact_root, "validation/sportshare_cv.json", payload)
    elif metric_case == "binary-denominator":
        payload = _read_json(artifact_root, "validation/binary_metrics.json")
        payload["binary_evaluable"] += 1
        _write_json(artifact_root, "validation/binary_metrics.json", payload)
    else:
        payload = _read_json(artifact_root, "validation/binary_metrics.json")
        payload["reference_labels"]["insufficient"] += 1
        _write_json(artifact_root, "validation/binary_metrics.json", payload)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="contract"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize("record_type", ["category", "region", "scenario"])
def test_rejects_duplicate_keyed_records(tmp_path, record_type):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    relative = {
        "category": "scale/category_scale.csv",
        "region": "scale/region_scale.csv",
        "scenario": "scale/scenarios.csv",
    }[record_type]
    rows = _read_csv(artifact_root, relative)
    rows.append(rows[0].copy())
    _write_csv(artifact_root, relative, rows)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="duplicate"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize("unsafe_path", ["../escape.txt", "/absolute.txt", "C:/absolute.txt"])
def test_rejects_unsafe_sha256sum_paths(tmp_path, unsafe_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    manifest_path = artifact_root / "SHA256SUMS"
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    digest, _relative = lines[0].split(maxsplit=1)
    lines[0] = f"{digest}  {unsafe_path}"
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="unsafe"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    "invalid_provenance",
    [
        "legacy test dataset",
        "FoRmAl",
        "synthetic formal source",
        True,
        {"type": "formal"},
    ],
)
def test_requires_typed_exact_formal_input_provenance(tmp_path, invalid_provenance):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    manifest = _read_json(artifact_root, "input_manifest.json")
    manifest["inputs"][0]["provenance"] = invalid_provenance
    _write_json(artifact_root, "input_manifest.json", manifest)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="provenance"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    "invalid_path",
    [
        "data/demo/input.csv",
        "data/test/input.csv",
        "data/LeGaCy/input.csv",
        "data/HiStOrIcAl/input.csv",
        "data/MoCk/input.csv",
        "data/synthetic/input.csv",
        "data/fallback/input.csv",
        "data\\DeMo\\input.csv",
        "archive/processed-batches/BATCH-20260803-R1/input.csv",
        "archive/processed/batch/BATCH-20260803-R1/input.csv",
        "archive/ProcessedBatch/BATCH-20260803-R1/input.csv",
    ],
)
def test_rejects_forbidden_normalized_input_path_segments(tmp_path, invalid_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    manifest = _read_json(artifact_root, "input_manifest.json")
    manifest["inputs"][0]["path"] = invalid_path
    _write_json(artifact_root, "input_manifest.json", manifest)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="input_manifest"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("data_version", "DATA-SyNtHeTiC-20260803"),
        ("model_version", "SPORTSCORE-historical-20260803"),
        ("sportshare_model_id", "SPORTSHARE-mock-20260803"),
        ("official_total_id", "SC-fallback-2022"),
    ],
)
def test_rejects_misleading_formal_identifiers_with_recomputed_hashes(
    tmp_path, field, invalid_value
):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    metadata = _read_json(artifact_root, "batch_metadata.json")
    metadata[field] = invalid_value
    _write_json(artifact_root, "batch_metadata.json", metadata)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match=field):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    "invalid_source_mode",
    ["demo", "test", "LeGaCy", "historical", "synthetic", "MoCk", "fallback", "FoRmAl"],
)
def test_source_mode_is_case_sensitive_exact_formal(tmp_path, invalid_source_mode):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    manifest = _read_json(artifact_root, "input_manifest.json")
    manifest["source_mode"] = invalid_source_mode
    _write_json(artifact_root, "input_manifest.json", manifest)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="source_mode"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("start_time", "not-an-iso-timestamp"),
        ("start_time", "2026-08-03T11:00:00"),
        ("end_time", "2026-08-03 12:00:00"),
        ("locked_at", "2026-08-03"),
    ],
)
def test_rejects_invalid_or_timezone_naive_lock_timestamps(tmp_path, field, invalid_value):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    metadata = _read_json(artifact_root, "batch_metadata.json")
    metadata[field] = invalid_value
    _write_json(artifact_root, "batch_metadata.json", metadata)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match=field):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize("ordering_case", ["start-after-end", "end-after-lock"])
def test_rejects_unordered_lock_timestamps(tmp_path, ordering_case):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    metadata = _read_json(artifact_root, "batch_metadata.json")
    if ordering_case == "start-after-end":
        metadata["start_time"] = "2026-08-03T13:00:00+08:00"
    else:
        metadata["locked_at"] = "2026-08-03T11:30:00+08:00"
    _write_json(artifact_root, "batch_metadata.json", metadata)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="timestamp order"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize("invalid_runtime", [True, ["python"], "{}", 1])
def test_runtime_environment_must_be_a_nonempty_object(tmp_path, invalid_runtime):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    metadata = _read_json(artifact_root, "batch_metadata.json")
    metadata["runtime_env_json"] = invalid_runtime
    _write_json(artifact_root, "batch_metadata.json", metadata)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="runtime_env_json"):
        validate_formal_artifact(artifact_root, expected)


def test_rejects_wrong_mapped_region_row_count_with_same_total(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    rows = _read_csv(artifact_root, "scale/region_scale.csv")
    removed = rows.pop()
    rows[-1]["scale_100m_cny"] = str(
        float(rows[-1]["scale_100m_cny"]) + float(removed["scale_100m_cny"])
    )
    rows[-1]["share"] = str(float(rows[-1]["share"]) + float(removed["share"]))
    _write_csv(artifact_root, "scale/region_scale.csv", rows)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="21 mapped"):
        validate_formal_artifact(artifact_root, expected)


def test_rejects_wrong_region_top_five_share_with_same_total(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    rows = _read_csv(artifact_root, "scale/region_scale.csv")
    rows[1]["scale_100m_cny"] = str(float(rows[1]["scale_100m_cny"]) + 1.0)
    rows[5]["scale_100m_cny"] = str(float(rows[5]["scale_100m_cny"]) - 1.0)
    total = expected["scale"]["official_total_100m_cny"]
    for row in (rows[1], rows[5]):
        row["share"] = str(float(row["scale_100m_cny"]) / total)
    _write_csv(artifact_root, "scale/region_scale.csv", rows)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="top-five"):
        validate_formal_artifact(artifact_root, expected)


def test_unresolved_region_rows_use_the_documented_sentinel(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    rows = _read_csv(artifact_root, "scale/region_scale.csv")
    rows[-1]["mapping_status"] = "unresolved"
    _write_csv(artifact_root, "scale/region_scale.csv", rows)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="__UNRESOLVED__"):
        validate_formal_artifact(artifact_root, expected)


def test_region_keys_must_be_exact_without_padding(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    rows = _read_csv(artifact_root, "scale/region_scale.csv")
    rows[-1]["region"] += " "
    _write_csv(artifact_root, "scale/region_scale.csv", rows)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="exact region"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("share-999", "share must be within"),
        ("negative-scale", "scale must be non-negative"),
        ("negative-share", "share must be within"),
        ("share-over-one", "share must be within"),
        ("inconsistent-share", "share must match scale"),
    ],
)
def test_every_non_chengdu_region_row_requires_a_valid_consistent_share(
    tmp_path, mutation, expected_error
):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    rows = _read_csv(artifact_root, "scale/region_scale.csv")
    target = rows[-1]
    total = expected["scale"]["official_total_100m_cny"]
    if mutation == "share-999":
        target["share"] = "999"
    elif mutation == "negative-scale":
        replacement = -1.0
        donor = rows[-2]
        donor["scale_100m_cny"] = str(
            float(donor["scale_100m_cny"])
            + float(target["scale_100m_cny"])
            - replacement
        )
        donor["share"] = str(float(donor["scale_100m_cny"]) / total)
        target["scale_100m_cny"] = str(replacement)
        target["share"] = "0"
    elif mutation == "negative-share":
        target["share"] = "-0.01"
    elif mutation == "share-over-one":
        target["share"] = "1.01"
    else:
        target["share"] = "0"
    _write_csv(artifact_root, "scale/region_scale.csv", rows)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match=expected_error):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    "relative",
    [
        "scale/category_scale.csv",
        "scale/region_scale.csv",
        "scale/scenarios.csv",
    ],
)
def test_csv_headers_must_remain_in_the_documented_order(tmp_path, relative):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    path = artifact_root / relative
    with path.open(encoding="utf-8", newline="") as stream:
        matrix = list(csv.reader(stream))
    for row in matrix:
        row[0], row[1] = row[1], row[0]
    with path.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows(matrix)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="header must be exactly"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize("mutation", ["profile", "alpha", "scenario-id"])
def test_scenarios_require_exact_grid_and_deterministic_ids(tmp_path, mutation):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    rows = _read_csv(artifact_root, "scale/scenarios.csv")
    row = next(
        item
        for item in rows
        if item["evidence_profile"] == "conservative" and float(item["alpha"]) == 0.10
    )
    if mutation == "profile":
        row["evidence_profile"] = "balanced"
        row["scenario_id"] = "balanced-alpha-0.10"
    elif mutation == "alpha":
        row["alpha"] = "0.15"
        row["scenario_id"] = "conservative-alpha-0.15"
    else:
        row["scenario_id"] = "SCENARIO-OPAQUE-01"
    _write_csv(artifact_root, "scale/scenarios.csv", rows)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="scenarios"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    ("canonical_alpha", "invalid_alpha"),
    [
        ("0.00", "0"),
        ("0.00", "0.0"),
        ("0.00", "-0.0"),
        ("0.00", "-0.00"),
        ("0.00", "0e0"),
        ("0.00", "0e-999"),
        ("0.00", "+0.00"),
        ("0.10", "0.1"),
        ("0.10", "0.100"),
        ("0.10", "1e-1"),
        ("0.10", "+0.10"),
    ],
)
def test_scenarios_reject_noncanonical_raw_alpha_tokens(
    tmp_path, canonical_alpha, invalid_alpha
):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    rows = _read_csv(artifact_root, "scale/scenarios.csv")
    row = next(
        item
        for item in rows
        if item["scenario_id"] == f"conservative-alpha-{canonical_alpha}"
    )
    row["alpha"] = invalid_alpha
    _write_csv(artifact_root, "scale/scenarios.csv", rows)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="canonical alpha token"):
        validate_formal_artifact(artifact_root, expected)


def test_duplicate_json_keys_are_rejected_from_raw_file(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    path = artifact_root / "batch_metadata.json"
    raw = path.read_text(encoding="utf-8")
    raw = raw.replace('  "mode": "formal",', '  "mode": "formal",\n  "mode": "formal",', 1)
    path.write_text(raw, encoding="utf-8")
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="duplicate JSON key"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "extra"])
def test_scenario_csv_rejects_ambiguous_raw_headers(tmp_path, mutation):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    path = artifact_root / "scale/scenarios.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        matrix = list(csv.reader(stream))
    if mutation == "duplicate":
        matrix[0].append("scenario_id")
        for row in matrix[1:]:
            row.append(row[0])
    elif mutation == "extra":
        matrix[0].append("unexpected")
        for row in matrix[1:]:
            row.append("ignored")
    else:
        index = matrix[0].index("boundary_in_100m_cny")
        for row in matrix:
            row.pop(index)
    with path.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows(matrix)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="header"):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    "missing_field", ["check_id", "name", "status", "expected", "actual", "detail"]
)
def test_every_audit_record_requires_all_contract_fields(tmp_path, missing_field):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    audit = _read_json(artifact_root, "audit/audit_checks.json")
    audit["checks"][0].pop(missing_field)
    _write_json(artifact_root, "audit/audit_checks.json", audit)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match=missing_field):
        validate_formal_artifact(artifact_root, expected)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("check_id", True),
        ("name", True),
        ("name", ""),
        ("status", 1),
        ("detail", 1),
        ("detail", " "),
        ("expected", {"value": True}),
        ("actual", [True]),
    ],
)
def test_audit_record_fields_have_sensible_types(tmp_path, field, invalid_value):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    audit = _read_json(artifact_root, "audit/audit_checks.json")
    audit["checks"][0][field] = invalid_value
    _write_json(artifact_root, "audit/audit_checks.json", audit)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match=field):
        validate_formal_artifact(artifact_root, expected)


def test_audit_records_require_24_unique_ids(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    audit = _read_json(artifact_root, "audit/audit_checks.json")
    audit["checks"][1]["check_id"] = audit["checks"][0]["check_id"]
    _write_json(artifact_root, "audit/audit_checks.json", audit)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="unique IDs"):
        validate_formal_artifact(artifact_root, expected)


def test_each_of_the_24_audit_records_must_pass(tmp_path):
    from tests.golden.formal_contract import validate_formal_artifact

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    artifact_root = _build_valid_artifact(tmp_path / expected["batch_number"], expected)
    audit = _read_json(artifact_root, "audit/audit_checks.json")
    audit["checks"][0]["status"] = "FAIL"
    _write_json(artifact_root, "audit/audit_checks.json", audit)
    _refresh_sha256sums(artifact_root)

    with pytest.raises(AssertionError, match="must PASS"):
        validate_formal_artifact(artifact_root, expected)
