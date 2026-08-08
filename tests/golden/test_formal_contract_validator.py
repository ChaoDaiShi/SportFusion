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
                    "provenance": "restricted formal source",
                }
            ],
        },
    )
    _write_json(root, "recognition/recognition_summary.json", expected["boundary"])
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
        [
            {
                "region": "成都市",
                "scale_100m_cny": scale["chengdu_100m_cny"],
                "share": scale["chengdu_share"],
            },
            {
                "region": "其他市州",
                "scale_100m_cny": (
                    scale["official_total_100m_cny"] - scale["chengdu_100m_cny"]
                ),
                "share": 1 - scale["chengdu_share"],
            },
        ],
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
        for alpha_index, alpha in enumerate((0.0, 0.10, 0.20, 0.30)):
            boundary_out = scale["boundary_out_100m_cny"]
            if profile_index == 0 and alpha_index == 0:
                boundary_out = scale["boundary_out_scenario_min_100m_cny"]
            elif profile_index == 2 and alpha_index == 3:
                boundary_out = scale["boundary_out_scenario_max_100m_cny"]
            scenario_rows.append(
                {
                    "scenario_id": f"{profile}-alpha-{alpha:.2f}",
                    "evidence_profile": profile,
                    "alpha": alpha,
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
