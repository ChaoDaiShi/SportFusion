"""Strict test-side contract for a locked SportFusion formal artifact.

The Phase 0 schema is deliberately small and explicit. ``batch_metadata.json`` carries
the Section 9.1 identity, version, hash, parameter, runtime, and lock fields.
``input_manifest.json`` repeats the batch/mode/input digest and declares one or more
inputs with ``path``, ``sha256``, and non-empty ``provenance``. Metric JSON files use
the names in the Golden fixture; category, region, and scenario CSV files are keyed by
``category``, ``region``, and ``scenario_id``. No aliases or legacy layouts are inferred.
"""

import csv
import hashlib
import json
import math
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

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

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_SHA256_LINE = re.compile(r"^([0-9a-fA-F]{64}) ([ *])(.+)$")
_FORBIDDEN_IDENTIFIER = re.compile(
    r"(?:^|[-_\s])(not[-_]?imported|demo|test|legacy)(?:$|[-_\s])", re.IGNORECASE
)
_LEGACY_PROCESSED_BATCH = re.compile(
    r"(?:^|/)processed_batch-[^/]+(?:/|$)", re.IGNORECASE
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _nonempty(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list, tuple, set)):
        return bool(value)
    return value is not None


def _number(value: object, area: str) -> float:
    _require(not isinstance(value, bool), f"contract {area}: expected a number")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise AssertionError(f"contract {area}: expected a number") from error
    _require(math.isfinite(number), f"contract {area}: expected a finite number")
    return number


def _close(actual: object, expected: object, tolerance: float, area: str) -> None:
    _require(
        math.isclose(
            _number(actual, area),
            _number(expected, area),
            rel_tol=0.0,
            abs_tol=tolerance,
        ),
        f"contract {area}: {actual!r} != {expected!r} within {tolerance}",
    )


def _read_json(root: Path, relative: str) -> dict:
    try:
        payload = json.loads((root / relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"contract {relative}: cannot read JSON") from error
    _require(isinstance(payload, dict), f"contract {relative}: expected a JSON object")
    return payload


def _read_csv(root: Path, relative: str) -> list[dict[str, str]]:
    try:
        with (root / relative).open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error) as error:
        raise AssertionError(f"contract {relative}: cannot read CSV") from error
    _require(rows, f"contract {relative}: expected at least one row")
    return rows


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_manifest_path(relative: str) -> bool:
    if not relative or "\\" in relative:
        return False
    posix = PurePosixPath(relative)
    windows = PureWindowsPath(relative)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        return False
    if relative != posix.as_posix() or any(part in {"", ".", ".."} for part in posix.parts):
        return False
    return posix.as_posix() != "."


def validate_sha256_manifest(artifact_root: Path) -> None:
    """Require a safe, duplicate-free, exact recursive raw-byte manifest."""
    manifest_path = artifact_root / "SHA256SUMS"
    _require(manifest_path.is_file(), "SHA256SUMS: missing manifest")
    try:
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise AssertionError("SHA256SUMS: cannot read manifest") from error
    _require(lines, "SHA256SUMS: manifest is empty")

    entries: dict[str, str] = {}
    for line_number, line in enumerate(lines, start=1):
        match = _SHA256_LINE.fullmatch(line)
        _require(match is not None, f"SHA256SUMS: malformed line {line_number}")
        digest, _mode, relative = match.groups()
        _require(
            _safe_manifest_path(relative),
            f"SHA256SUMS: unsafe path on line {line_number}: {relative!r}",
        )
        _require(relative not in entries, f"SHA256SUMS: duplicate entry {relative!r}")
        entries[relative] = digest.lower()

    actual_files = {
        path.relative_to(artifact_root).as_posix(): path
        for path in artifact_root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    entry_names = set(entries)
    actual_names = set(actual_files)
    _require(
        entry_names == actual_names,
        "SHA256SUMS: exact recursive coverage mismatch; "
        f"missing={sorted(actual_names - entry_names)!r}, "
        f"extra={sorted(entry_names - actual_names)!r}",
    )
    for relative, path in actual_files.items():
        _require(
            entries[relative] == _sha256_file(path),
            f"SHA256SUMS: raw-byte hash mismatch for {relative}",
        )


def _validate_required_files(artifact_root: Path) -> None:
    missing = [relative for relative in REQUIRED if not (artifact_root / relative).is_file()]
    _require(not missing, f"contract required files: missing {missing!r}")


def _validate_batch_metadata(metadata: dict, expected: dict) -> None:
    area = "batch_metadata"
    _require(metadata.get("batch_number") == expected["batch_number"], f"{area}: batch mismatch")
    _require(metadata.get("mode") == "formal", f"{area}: mode must be exactly formal")
    _require(
        metadata.get("status") == "formal-completed",
        f"{area}: status must be exactly formal-completed",
    )
    for field in ("start_time", "end_time", "locked_at", "runtime_env_json"):
        _require(_nonempty(metadata.get(field)), f"{area}: {field} must be non-empty")

    identifiers = (
        "data_version",
        "model_version",
        "feature_version",
        "dictionary_version",
        "code_map_version",
        "sportshare_model_id",
        "evidence_calibration_version",
        "scale_config_version",
        "official_total_id",
    )
    for field in identifiers:
        value = metadata.get(field)
        _require(isinstance(value, str) and value.strip(), f"{area}: {field} must be non-empty")
        _require(
            _FORBIDDEN_IDENTIFIER.search(value) is None,
            f"{area}: {field} cannot identify NOT-IMPORTED/demo/test/legacy state",
        )

    for field in (
        "dictionary_sha256",
        "code_map_sha256",
        "sportshare_model_sha256",
        "input_file_sha256",
    ):
        value = metadata.get(field)
        _require(
            isinstance(value, str) and _SHA256.fullmatch(value) is not None,
            f"{area}: {field} must be 64 hexadecimal characters",
        )

    threshold = _number(metadata.get("candidate_threshold"), f"{area}.candidate_threshold")
    _require(0.0 < threshold <= 1.0, f"{area}: candidate_threshold must be explicit and valid")
    scale = expected["scale"]
    _close(metadata.get("alpha"), scale["baseline_alpha"], 1e-9, f"{area}.alpha")
    _close(
        metadata.get("official_total_100m_cny"),
        scale["official_total_100m_cny"],
        0.02,
        f"{area}.official_total_100m_cny",
    )


def _validate_input_manifest(manifest: dict, metadata: dict, expected: dict) -> None:
    area = "input_manifest"
    _require(manifest.get("batch_number") == expected["batch_number"], f"{area}: batch mismatch")
    _require(manifest.get("batch_number") == metadata["batch_number"], f"{area}: metadata mismatch")
    _require(manifest.get("mode") == "formal", f"{area}: mode must be exactly formal")
    _require(manifest.get("mode") == metadata["mode"], f"{area}: metadata mode mismatch")
    _require(manifest.get("source_mode") == "formal", f"{area}: demo/legacy source mode rejected")
    digest = manifest.get("input_file_sha256")
    _require(
        isinstance(digest, str) and _SHA256.fullmatch(digest) is not None,
        f"{area}: input_file_sha256 must be a SHA256",
    )
    _require(digest == metadata["input_file_sha256"], f"{area}: input hash mismatch")

    inputs = manifest.get("inputs")
    _require(isinstance(inputs, list) and inputs, f"{area}: inputs must be a non-empty list")
    declared_hashes = []
    for index, declared in enumerate(inputs):
        _require(isinstance(declared, dict), f"{area}: input {index} must be an object")
        path = declared.get("path")
        _require(isinstance(path, str) and path.strip(), f"{area}: input {index} path is required")
        normalized_path = path.replace("\\", "/")
        _require(
            _LEGACY_PROCESSED_BATCH.search(normalized_path) is None,
            f"{area}: legacy processed batch path rejected: {path}",
        )
        item_digest = declared.get("sha256")
        _require(
            isinstance(item_digest, str) and _SHA256.fullmatch(item_digest) is not None,
            f"{area}: input {index} sha256 must be 64 hexadecimal characters",
        )
        _require(
            _nonempty(declared.get("provenance")),
            f"{area}: input {index} provenance is required",
        )
        declared_hashes.append(item_digest)
    _require(digest in declared_hashes, f"{area}: no declared input binds the batch input hash")


def _validate_recognition(root: Path, expected: dict) -> None:
    recognition = _read_json(root, "recognition/recognition_summary.json")
    boundary = expected["boundary"]
    for field, locked_value in boundary.items():
        _require(field in recognition, f"recognition contract: missing {field}")
        if field.endswith("_rate"):
            _close(recognition[field], locked_value, 1e-4, f"recognition.{field}")
        else:
            _require(
                recognition[field] == locked_value,
                f"recognition contract: {field} differs from the locked value",
            )


def _validate_evidence_and_sportshare(root: Path, expected: dict) -> None:
    evidence = _read_json(root, "recognition/evidence_group_summary.json")
    _require(evidence == expected["evidence_groups"], "evidence contract: keyed distribution mismatch")

    summary = _read_json(root, "sportshare/sportshare_summary.json")
    _require(
        summary.get("sources") == expected["sportshare_sources"],
        "contract sportshare sources: keyed distribution mismatch",
    )
    _require(
        summary.get("total_share_results") == expected["boundary"]["fusion_count"],
        "contract sportshare sources: total_share_results mismatch",
    )


def _key_rows(rows: list[dict[str, str]], key: str, area: str) -> dict[str, dict[str, str]]:
    keyed = {}
    for row in rows:
        value = row.get(key)
        _require(value is not None and value.strip(), f"contract {area}: missing {key}")
        _require(value not in keyed, f"contract {area}: duplicate {key} {value!r}")
        keyed[value] = row
    return keyed


def _validate_scale(root: Path, expected: dict) -> None:
    scale = expected["scale"]
    total = scale["official_total_100m_cny"]

    category_rows = _read_csv(root, "scale/category_scale.csv")
    categories = _key_rows(category_rows, "category", "category scale")
    locked_categories = scale["category_scale_100m_cny"]
    _require(set(categories) == set(locked_categories), "contract category scale: key set mismatch")
    for category, locked_value in locked_categories.items():
        _close(
            categories[category].get("scale_100m_cny"),
            locked_value,
            0.02,
            f"category scale {category}",
        )
    _close(
        sum(_number(row.get("scale_100m_cny"), "category scale") for row in category_rows),
        total,
        0.02,
        "category scale official total",
    )

    boundary = _read_json(root, "scale/boundary_scale.json")
    for field, tolerance in (
        ("official_total_100m_cny", 0.02),
        ("alpha", 1e-9),
        ("boundary_in_100m_cny", 0.02),
        ("boundary_out_100m_cny", 0.02),
        ("boundary_out_share", 1e-4),
    ):
        locked_field = "baseline_alpha" if field == "alpha" else field
        _close(boundary.get(field), scale[locked_field], tolerance, f"boundary scale {field}")
    for field in ("mapped_enterprises", "unresolved_enterprises"):
        _require(
            boundary.get(field) == scale[field],
            f"contract boundary scale: {field} differs from the locked value",
        )
    _close(
        _number(boundary["boundary_in_100m_cny"], "boundary in")
        + _number(boundary["boundary_out_100m_cny"], "boundary out"),
        total,
        0.02,
        "boundary scale total",
    )
    _require(
        boundary["mapped_enterprises"] + boundary["unresolved_enterprises"]
        == expected["boundary"]["fusion_count"],
        "contract boundary scale: mapped plus unresolved mismatch",
    )

    region_rows = _read_csv(root, "scale/region_scale.csv")
    regions = _key_rows(region_rows, "region", "region scale")
    _close(
        sum(_number(row.get("scale_100m_cny"), "region scale") for row in region_rows),
        total,
        0.02,
        "region scale official total",
    )
    _require("成都市" in regions, "contract region scale: missing locked Chengdu row")
    _close(
        regions["成都市"].get("scale_100m_cny"),
        scale["chengdu_100m_cny"],
        0.02,
        "region scale Chengdu value",
    )
    _close(
        regions["成都市"].get("share"),
        scale["chengdu_share"],
        1e-4,
        "region scale Chengdu share",
    )

    scenario_rows = _read_csv(root, "scale/scenarios.csv")
    _key_rows(scenario_rows, "scenario_id", "scenarios")
    _require(
        len(scenario_rows) == scale["scenario_count"],
        "contract scenarios: expected exactly 12 rows",
    )
    parameter_keys = set()
    boundary_out_values = []
    baseline_rows = []
    for row in scenario_rows:
        profile = row.get("evidence_profile")
        _require(profile is not None and profile.strip(), "contract scenarios: evidence_profile required")
        alpha = _number(row.get("alpha"), "scenarios alpha")
        parameter_key = (profile, alpha)
        _require(parameter_key not in parameter_keys, "contract scenarios: duplicate parameter row")
        parameter_keys.add(parameter_key)
        scenario_total = _number(row.get("total_output_100m_cny"), "scenarios total")
        boundary_in = _number(row.get("boundary_in_100m_cny"), "scenarios boundary in")
        boundary_out = _number(row.get("boundary_out_100m_cny"), "scenarios boundary out")
        _close(scenario_total, total, 0.02, "scenarios official total")
        _close(boundary_in + boundary_out, total, 0.02, "scenarios boundary total")
        boundary_out_values.append(boundary_out)
        if profile == "baseline" and math.isclose(
            alpha, scale["baseline_alpha"], rel_tol=0.0, abs_tol=1e-9
        ):
            baseline_rows.append(row)
    _require(len(baseline_rows) == 1, "contract scenarios: one baseline alpha row required")
    baseline = baseline_rows[0]
    _close(
        baseline.get("boundary_in_100m_cny"),
        scale["boundary_in_100m_cny"],
        0.02,
        "scenarios baseline boundary in",
    )
    _close(
        baseline.get("boundary_out_100m_cny"),
        scale["boundary_out_100m_cny"],
        0.02,
        "scenarios baseline boundary out",
    )
    _close(
        min(boundary_out_values),
        scale["boundary_out_scenario_min_100m_cny"],
        0.02,
        "scenarios boundary out minimum",
    )
    _close(
        max(boundary_out_values),
        scale["boundary_out_scenario_max_100m_cny"],
        0.02,
        "scenarios boundary out maximum",
    )


def _validate_metrics(root: Path, expected: dict) -> None:
    validation = expected["validation"]
    binary = _read_json(root, "validation/binary_metrics.json")
    category = _read_json(root, "validation/category_metrics.json")
    sportshare = _read_json(root, "validation/sportshare_cv.json")
    for field, locked_value in validation["binary"].items():
        _close(binary.get(field), locked_value, 1e-4, f"binary metrics {field}")
    for field, locked_value in validation["category"].items():
        _close(category.get(field), locked_value, 1e-4, f"category metrics {field}")
    for field, locked_value in validation["sportshare"].items():
        _close(sportshare.get(field), locked_value, 1e-4, f"sportshare metrics {field}")
    _require(
        binary.get("binary_evaluable") == validation["binary_evaluable"],
        "contract binary metrics: binary_evaluable mismatch",
    )
    _require(
        category.get("category_evaluable") == validation["category_evaluable"],
        "contract category metrics: category_evaluable mismatch",
    )
    _require(
        binary.get("reference_labels") == validation["reference_labels"],
        "contract binary metrics: reference_labels mismatch",
    )


def _validate_audit(root: Path, expected: dict) -> None:
    audit = _read_json(root, "audit/audit_checks.json")
    locked = expected["validation"]["audit"]
    _require(audit.get("pass_count") == locked["passed"] == 24, "audit contract: pass_count")
    _require(audit.get("total") == locked["total"] == 24, "audit contract: total")
    checks = audit.get("checks")
    _require(isinstance(checks, list) and len(checks) == 24, "audit contract: exactly 24 checks")
    identifiers = []
    for index, check in enumerate(checks):
        _require(isinstance(check, dict), f"audit contract: check {index} must be an object")
        check_id = check.get("check_id")
        _require(isinstance(check_id, str) and check_id.strip(), "audit contract: check_id required")
        identifiers.append(check_id)
        _require(check.get("status") == "PASS", f"audit contract: {check_id} must PASS")
    _require(len(set(identifiers)) == 24, "audit contract: checks must have unique IDs")


def validate_formal_artifact(artifact_root: Path, expected: dict) -> None:
    """Validate provenance, every locked metric, audit state, and file hashes."""
    _validate_required_files(artifact_root)
    validate_sha256_manifest(artifact_root)
    metadata = _read_json(artifact_root, "batch_metadata.json")
    _validate_batch_metadata(metadata, expected)
    manifest = _read_json(artifact_root, "input_manifest.json")
    _validate_input_manifest(manifest, metadata, expected)
    _validate_recognition(artifact_root, expected)
    _validate_evidence_and_sportshare(artifact_root, expected)
    _validate_scale(artifact_root, expected)
    _validate_metrics(artifact_root, expected)
    _validate_audit(artifact_root, expected)
