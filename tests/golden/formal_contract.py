"""Strict test-side contract for a locked SportFusion formal artifact.

The Phase 0 schema is deliberately small and explicit. ``batch_metadata.json`` carries
the Section 9.1 identity, version, hash, parameter, runtime, and lock fields.
``input_manifest.json`` repeats the batch/mode/input digest and declares one or more
inputs with ``path``, ``sha256``, and the typed exact provenance string ``"formal"``.
Metric JSON files use the names in the Golden fixture. CSV headers are exact: category
rows use ``category,scale_100m_cny``; region rows use
``region,scale_100m_cny,share,mapping_status``; and scenario rows use
``scenario_id,evidence_profile,alpha,total_output_100m_cny,boundary_in_100m_cny,``
``boundary_out_100m_cny``. Region output has exactly 21 ``mapped`` rows. An unresolved
aggregate is optional, but if present it is one ``mapping_status=unresolved`` row with
the exact key ``__UNRESOLVED__`` and is excluded from the mapped-row/CR5 calculation.
Scenario IDs are exactly ``{evidence_profile}-alpha-{alpha:.2f}``. No aliases, duplicate
JSON keys, duplicate CSV headers, or legacy layouts are inferred.
"""

import csv
import hashlib
import json
import math
import re
from datetime import datetime
from itertools import pairwise
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
_FORBIDDEN_MARKERS = {
    "demo",
    "fallback",
    "historical",
    "legacy",
    "mock",
    "synthetic",
    "test",
}
_CSV_HEADERS = {
    "scale/category_scale.csv": ("category", "scale_100m_cny"),
    "scale/region_scale.csv": ("region", "scale_100m_cny", "share", "mapping_status"),
    "scale/scenarios.csv": (
        "scenario_id",
        "evidence_profile",
        "alpha",
        "total_output_100m_cny",
        "boundary_in_100m_cny",
        "boundary_out_100m_cny",
    ),
}
_SCENARIO_PROFILES = ("conservative", "baseline", "expanded")
_SCENARIO_ALPHAS = (0.0, 0.10, 0.20, 0.30)


class _DuplicateJsonKey(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _normalized_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def _has_forbidden_marker(value: str) -> bool:
    tokens = _normalized_tokens(value)
    return any(token in _FORBIDDEN_MARKERS for token in tokens) or any(
        first == "not" and second == "imported"
        for first, second in pairwise(tokens)
    )


def _is_processed_batch_path(value: str) -> bool:
    tokens = _normalized_tokens(value.replace("\\", "/"))
    compact_tokens = {token.rstrip("es") for token in tokens}
    return "processedbatch" in compact_tokens or (
        "processed" in compact_tokens and "batch" in compact_tokens
    )


def _duplicate_aware_object(pairs: list[tuple[str, object]]) -> dict:
    payload = {}
    for key, value in pairs:
        if key in payload:
            raise _DuplicateJsonKey(key)
        payload[key] = value
    return payload


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
        payload = json.loads(
            (root / relative).read_text(encoding="utf-8"),
            object_pairs_hook=_duplicate_aware_object,
        )
    except _DuplicateJsonKey as error:
        raise AssertionError(
            f"contract {relative}: duplicate JSON key {error.args[0]!r}"
        ) from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"contract {relative}: cannot read JSON") from error
    _require(isinstance(payload, dict), f"contract {relative}: expected a JSON object")
    return payload


def _read_csv(root: Path, relative: str) -> list[dict[str, str]]:
    try:
        with (root / relative).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames
            _require(headers is not None, f"contract {relative}: missing CSV header")
            _require(
                len(headers) == len(set(headers)),
                f"contract {relative}: duplicate CSV header",
            )
            expected_headers = _CSV_HEADERS[relative]
            _require(
                set(headers) == set(expected_headers),
                f"contract {relative}: header must contain exactly {expected_headers!r}",
            )
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as error:
        raise AssertionError(f"contract {relative}: cannot read CSV") from error
    _require(rows, f"contract {relative}: expected at least one row")
    for index, row in enumerate(rows, start=1):
        _require(
            set(row) == set(expected_headers) and all(value is not None for value in row.values()),
            f"contract {relative}: row {index} must contain the exact CSV keys",
        )
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


def _timestamp(value: object, area: str) -> datetime:
    _require(isinstance(value, str) and value.strip(), f"{area}: must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise AssertionError(f"{area}: must be an ISO-8601 timestamp") from error
    _require(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        f"{area}: timestamp must be timezone-aware",
    )
    return parsed


def _validate_batch_metadata(metadata: dict, expected: dict) -> None:
    area = "batch_metadata"
    _require(metadata.get("batch_number") == expected["batch_number"], f"{area}: batch mismatch")
    _require(metadata.get("mode") == "formal", f"{area}: mode must be exactly formal")
    _require(
        metadata.get("status") == "formal-completed",
        f"{area}: status must be exactly formal-completed",
    )
    start_time = _timestamp(metadata.get("start_time"), f"{area}: start_time")
    end_time = _timestamp(metadata.get("end_time"), f"{area}: end_time")
    locked_at = _timestamp(metadata.get("locked_at"), f"{area}: locked_at")
    _require(
        start_time <= end_time <= locked_at,
        f"{area}: timestamp order must be start_time <= end_time <= locked_at",
    )
    runtime_env = metadata.get("runtime_env_json")
    _require(
        isinstance(runtime_env, dict) and bool(runtime_env),
        f"{area}: runtime_env_json must be a non-empty object",
    )

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
            not _has_forbidden_marker(value),
            f"{area}: {field} cannot identify a forbidden formal-data state",
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
    _require(
        manifest.get("source_mode") == "formal",
        f"{area}: source_mode must be exactly formal",
    )
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
            not _has_forbidden_marker(normalized_path),
            f"{area}: forbidden marker in input path: {path}",
        )
        _require(
            not _is_processed_batch_path(normalized_path),
            f"{area}: legacy/processed batch path rejected: {path}",
        )
        item_digest = declared.get("sha256")
        _require(
            isinstance(item_digest, str) and _SHA256.fullmatch(item_digest) is not None,
            f"{area}: input {index} sha256 must be 64 hexadecimal characters",
        )
        provenance = declared.get("provenance")
        _require(
            isinstance(provenance, str) and provenance == "formal",
            f"{area}: input {index} provenance must be the typed exact value 'formal'",
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
        _require(value == value.strip(), f"contract {area}: exact {key} keys cannot be padded")
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
    mapped_region_rows = []
    unresolved_region_rows = []
    for row in region_rows:
        mapping_status = row.get("mapping_status")
        if mapping_status == "mapped":
            _require(
                row["region"] != "__UNRESOLVED__",
                "contract region scale: __UNRESOLVED__ cannot be marked mapped",
            )
            mapped_region_rows.append(row)
        elif mapping_status == "unresolved":
            _require(
                row["region"] == "__UNRESOLVED__",
                "contract region scale: unresolved row must use __UNRESOLVED__",
            )
            unresolved_region_rows.append(row)
        else:
            raise AssertionError(
                "contract region scale: mapping_status must be mapped or unresolved"
            )
    _require(
        len(mapped_region_rows) == scale["region_mapped_row_count"] == 21,
        "contract region scale: expected exactly 21 mapped rows",
    )
    _require(
        len(unresolved_region_rows) <= 1,
        "contract region scale: at most one __UNRESOLVED__ row is allowed",
    )
    _close(
        sum(_number(row.get("scale_100m_cny"), "region scale") for row in region_rows),
        total,
        0.02,
        "region scale official total",
    )
    _require("成都市" in regions, "contract region scale: missing locked Chengdu row")
    _require(
        regions["成都市"].get("mapping_status") == "mapped",
        "contract region scale: Chengdu must be a mapped row",
    )
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
    mapped_values = sorted(
        (
            _number(row.get("scale_100m_cny"), "region scale mapped value")
            for row in mapped_region_rows
        ),
        reverse=True,
    )
    _close(
        sum(mapped_values[:5]) / total,
        scale["region_top_five_share"],
        1e-4,
        "region scale top-five share",
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
        _require(
            profile is not None and profile == profile.strip() and profile,
            "contract scenarios: evidence_profile must be exact",
        )
        alpha = _number(row.get("alpha"), "scenarios alpha")
        parameter_key = (profile, alpha)
        _require(parameter_key not in parameter_keys, "contract scenarios: duplicate parameter row")
        parameter_keys.add(parameter_key)
        expected_scenario_id = f"{profile}-alpha-{alpha:.2f}"
        _require(
            row.get("scenario_id") == expected_scenario_id,
            "contract scenarios: scenario_id must bind evidence_profile and alpha as "
            "{evidence_profile}-alpha-{alpha:.2f}",
        )
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
    expected_parameter_keys = {
        (profile, alpha)
        for profile in _SCENARIO_PROFILES
        for alpha in _SCENARIO_ALPHAS
    }
    _require(
        parameter_keys == expected_parameter_keys,
        "contract scenarios: parameter rows must equal the exact 3 x 4 profile/alpha grid",
    )
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
    required_fields = {"check_id", "name", "status", "expected", "actual", "detail"}
    for index, check in enumerate(checks):
        _require(isinstance(check, dict), f"audit contract: check {index} must be an object")
        missing_fields = required_fields - set(check)
        _require(
            not missing_fields,
            f"audit contract: check {index} missing fields {sorted(missing_fields)!r}",
        )
        check_id = check.get("check_id")
        _require(isinstance(check_id, str) and check_id.strip(), "audit contract: check_id required")
        identifiers.append(check_id)
        _require(
            check.get("status") == "PASS",
            f"audit contract: {check_id} status must PASS",
        )
        for field in ("name", "detail"):
            value = check.get(field)
            _require(
                isinstance(value, str) and value.strip(),
                f"audit contract: {check_id} {field} must be a non-empty string",
            )
        for field in ("expected", "actual"):
            value = check.get(field)
            _require(
                isinstance(value, (str, int, float, bool))
                and (not isinstance(value, float) or math.isfinite(value)),
                f"audit contract: {check_id} {field} must be a finite JSON scalar",
            )
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
