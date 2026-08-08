"""Strict test-side contract for a locked SportFusion formal artifact.

The Phase 0 schema covers the complete 20-file competition artifact tree and is
deliberately explicit. ``batch_metadata.json`` carries
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
``recognition/recognition_summary.json`` nests the exact fixture-backed
``review_priority`` distribution with only ``P1`` through ``P4``. Scenario alpha fields
are raw canonical tokens ``0.00``, ``0.10``, ``0.20``, and ``0.30``; scenario IDs are the
direct 3-by-4 set ``{evidence_profile}-alpha-{alpha_token}``. No aliases, duplicate JSON
keys, duplicate CSV headers, or legacy layouts are inferred. Parquet artifacts are
required to be non-empty and are bound by ``SHA256SUMS`` without interpreting their
contents in Phase 0. ``audit/benchmark.json`` distinguishes an explicit
``not_measured`` state (all new measurements null/empty, especially peak memory) from
a complete finite non-negative ``measured`` result, so historical runtime cannot be
silently presented as a newly executed benchmark.
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
    "recognition/enterprise_boundaries.parquet",
    "sportshare/sportshare_summary.json",
    "sportshare/sportshare_results.parquet",
    "scale/category_scale.csv",
    "scale/region_scale.csv",
    "scale/boundary_scale.json",
    "scale/scenarios.csv",
    "validation/binary_metrics.json",
    "validation/category_metrics.json",
    "validation/baselines.csv",
    "validation/threshold_sweep.csv",
    "validation/ablation.csv",
    "validation/sportshare_cv.json",
    "audit/audit_checks.json",
    "audit/benchmark.json",
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
    "validation/baselines.csv": (
        "baseline_id",
        "sample_count",
        "true_negative",
        "false_positive",
        "false_negative",
        "true_positive",
        "accuracy",
        "precision",
        "recall",
        "f1",
    ),
    "validation/threshold_sweep.csv": (
        "threshold",
        "candidate_count",
        "precision",
        "recall",
        "f1",
        "false_negative",
        "false_positive",
    ),
    "validation/ablation.csv": (
        "ablation_id",
        "removed_component",
        "recall",
        "f1",
    ),
}
_SCENARIO_PROFILES = ("conservative", "baseline", "expanded")
_SCENARIO_ALPHA_TOKENS = ("0.00", "0.10", "0.20", "0.30")
_CANONICAL_SCENARIO_IDS = frozenset(
    f"{profile}-alpha-{alpha_token}"
    for profile in _SCENARIO_PROFILES
    for alpha_token in _SCENARIO_ALPHA_TOKENS
)


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


def _integer(value: object, area: str) -> int:
    number = _number(value, area)
    _require(number.is_integer(), f"contract {area}: expected an integer")
    return int(number)


def _rate(value: object, area: str) -> float:
    number = _number(value, area)
    _require(0.0 <= number <= 1.0, f"contract {area}: expected a value within [0, 1]")
    return number


def _exact_keys(payload: dict, keys: set[str], area: str) -> None:
    _require(
        set(payload) == keys,
        f"contract {area}: keys must be exactly {sorted(keys)!r}",
    )


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
            missing_headers = sorted(set(expected_headers) - set(headers))
            extra_headers = sorted(set(headers) - set(expected_headers))
            _require(
                set(headers) == set(expected_headers),
                f"contract {relative}: header must contain exactly {expected_headers!r}; "
                f"missing={missing_headers!r}, extra={extra_headers!r}",
            )
            _require(
                tuple(headers) == expected_headers,
                f"contract {relative}: header must be exactly {expected_headers!r} "
                "in documented order",
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
    for relative in (
        "recognition/enterprise_boundaries.parquet",
        "sportshare/sportshare_results.parquet",
    ):
        _require(
            (artifact_root / relative).stat().st_size > 0,
            f"contract required parquet: {relative} must be non-empty",
        )


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
    review_priority = recognition.get("review_priority")
    _require(
        isinstance(review_priority, dict),
        "recognition contract: missing review priority distribution",
    )
    _require(
        review_priority == expected["review_priority"],
        "recognition contract: review priority distribution must match exact fixture keys and counts",
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
        region = row["region"]
        row_scale = _number(row.get("scale_100m_cny"), f"region scale {region} scale")
        _require(
            row_scale >= 0.0,
            f"contract region scale {region}: scale must be non-negative",
        )
        row_share = _number(row.get("share"), f"region scale {region} share")
        _require(
            0.0 <= row_share <= 1.0,
            f"contract region scale {region}: share must be within [0, 1]",
        )
        _close(
            row_share,
            row_scale / total,
            1e-4,
            f"region scale {region}: share must match scale / official total",
        )
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
    scenario_ids = _key_rows(scenario_rows, "scenario_id", "scenarios")
    _require(
        len(scenario_rows) == scale["scenario_count"],
        "contract scenarios: expected exactly 12 rows",
    )
    _require(
        set(scenario_ids) == _CANONICAL_SCENARIO_IDS,
        "contract scenarios: scenario IDs must equal the canonical 3 x 4 ID set",
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
        alpha_token = row.get("alpha")
        _require(
            alpha_token in _SCENARIO_ALPHA_TOKENS,
            "contract scenarios: alpha must use a canonical alpha token",
        )
        parameter_key = (profile, alpha_token)
        _require(parameter_key not in parameter_keys, "contract scenarios: duplicate parameter row")
        parameter_keys.add(parameter_key)
        expected_scenario_id = f"{profile}-alpha-{alpha_token}"
        _require(
            row.get("scenario_id") == expected_scenario_id,
            "contract scenarios: scenario_id must bind evidence_profile and canonical alpha token",
        )
        scenario_total = _number(row.get("total_output_100m_cny"), "scenarios total")
        boundary_in = _number(row.get("boundary_in_100m_cny"), "scenarios boundary in")
        boundary_out = _number(row.get("boundary_out_100m_cny"), "scenarios boundary out")
        _close(scenario_total, total, 0.02, "scenarios official total")
        _close(boundary_in + boundary_out, total, 0.02, "scenarios boundary total")
        boundary_out_values.append(boundary_out)
        if profile == "baseline" and alpha_token == f"{scale['baseline_alpha']:.2f}":
            baseline_rows.append(row)
    expected_parameter_keys = {
        (profile, alpha_token)
        for profile in _SCENARIO_PROFILES
        for alpha_token in _SCENARIO_ALPHA_TOKENS
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


def _validate_binary_metrics(root: Path, validation: dict) -> None:
    area = "binary metrics"
    binary = _read_json(root, "validation/binary_metrics.json")
    for field in ("accuracy", "precision", "recall", "f1"):
        _close(binary.get(field), validation["binary"][field], 1e-4, f"{area} {field}")
    _require(
        binary.get("binary_evaluable") == validation["binary_evaluable"],
        f"contract {area}: binary_evaluable mismatch",
    )
    _require(
        binary.get("reference_labels") == validation["reference_labels"],
        f"contract {area}: reference_labels mismatch",
    )

    matrix = binary.get("confusion_matrix")
    _require(isinstance(matrix, dict), f"contract {area}: confusion_matrix required")
    matrix_keys = {"true_negative", "false_positive", "false_negative", "true_positive"}
    _exact_keys(matrix, matrix_keys, f"{area} confusion_matrix")
    counts = {key: _integer(matrix[key], f"{area} {key}") for key in matrix_keys}
    _require(all(value >= 0 for value in counts.values()), f"contract {area}: counts must be non-negative")
    _require(
        sum(counts.values()) == validation["binary_evaluable"],
        f"contract {area}: confusion matrix total mismatch",
    )
    _require(
        counts["false_negative"] == validation["binary"]["false_negative"],
        f"contract {area}: false_negative must be 1",
    )
    _require(
        counts["true_positive"] + counts["false_negative"]
        == validation["reference_labels"]["sport"],
        f"contract {area}: positive-class support mismatch",
    )
    _require(
        counts["true_negative"] + counts["false_positive"]
        == validation["reference_labels"]["non_sport"],
        f"contract {area}: negative-class support mismatch",
    )
    tp = counts["true_positive"]
    tn = counts["true_negative"]
    fp = counts["false_positive"]
    fn = counts["false_negative"]
    calculated_precision = tp / (tp + fp)
    calculated_recall = tp / (tp + fn)
    calculated = {
        "accuracy": (tp + tn) / sum(counts.values()),
        "precision": calculated_precision,
        "recall": calculated_recall,
        "f1": 2 * calculated_precision * calculated_recall / (
            calculated_precision + calculated_recall
        ),
    }
    for field, value in calculated.items():
        _close(binary.get(field), value, 1e-4, f"{area} {field} consistency")


def _validate_baselines(root: Path, validation: dict) -> None:
    area = "baseline metrics"
    rows = _read_csv(root, "validation/baselines.csv")
    baselines = _key_rows(rows, "baseline_id", area)
    locked = validation["baselines"]
    _require(set(baselines) == set(locked["ids"]), f"contract {area}: baseline IDs mismatch")
    for baseline_id, row in baselines.items():
        sample_count = _integer(row["sample_count"], f"{area} {baseline_id} sample_count")
        counts = {
            field: _integer(row[field], f"{area} {baseline_id} {field}")
            for field in ("true_negative", "false_positive", "false_negative", "true_positive")
        }
        _require(
            all(value >= 0 for value in counts.values()),
            f"contract {area} {baseline_id}: counts must be non-negative",
        )
        _require(
            sample_count == validation["binary_evaluable"] == sum(counts.values()),
            f"contract {area} {baseline_id}: confusion matrix total mismatch",
        )
        tp = counts["true_positive"]
        tn = counts["true_negative"]
        fp = counts["false_positive"]
        fn = counts["false_negative"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        calculated = {
            "accuracy": (tp + tn) / sample_count,
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        }
        for field, value in calculated.items():
            _rate(row[field], f"{area} {baseline_id} {field}")
            _close(row[field], value, 1e-4, f"{area} {baseline_id} {field} consistency")
    _require(
        _integer(baselines["traditional_direct_code"]["false_negative"], f"{area} traditional FN")
        == locked["traditional_direct_code_false_negative"],
        f"contract {area}: traditional direct-code false_negative must be 24",
    )
    _require(
        _integer(baselines["sportfusion"]["false_negative"], f"{area} SportFusion FN")
        == locked["sportfusion_false_negative"],
        f"contract {area}: SportFusion false_negative must be 1",
    )
    for field in ("accuracy", "precision", "recall", "f1"):
        _close(
            baselines["sportfusion"][field],
            validation["binary"][field],
            1e-4,
            f"{area} SportFusion {field}",
        )


def _validate_category_metrics(root: Path, expected: dict) -> None:
    area = "category metrics"
    validation = expected["validation"]
    category = _read_json(root, "validation/category_metrics.json")
    for field in ("accuracy", "macro_f1"):
        _close(category.get(field), validation["category"][field], 1e-4, f"{area} {field}")
    _require(
        category.get("correct") == validation["category"]["correct"],
        f"contract {area}: correct count mismatch",
    )
    _require(
        category.get("category_evaluable") == validation["category_evaluable"],
        f"contract {area}: category_evaluable mismatch",
    )
    category_keys = set(expected["scale"]["category_scale_100m_cny"])
    matrix = category.get("confusion_matrix")
    per_class = category.get("per_class")
    _require(isinstance(matrix, dict), f"contract {area}: confusion_matrix required")
    _require(isinstance(per_class, dict), f"contract {area}: per_class required")
    _require(set(matrix) == category_keys, f"contract {area}: confusion row keys mismatch")
    _require(set(per_class) == category_keys, f"contract {area}: per-class keys mismatch")

    matrix_counts = {}
    for actual, row in matrix.items():
        _require(isinstance(row, dict), f"contract {area}: confusion row {actual!r} must be an object")
        _require(set(row) == category_keys, f"contract {area}: confusion column keys mismatch")
        matrix_counts[actual] = {
            predicted: _integer(value, f"{area} confusion {actual}/{predicted}")
            for predicted, value in row.items()
        }
        _require(
            all(value >= 0 for value in matrix_counts[actual].values()),
            f"contract {area}: confusion counts must be non-negative",
        )
    total = sum(sum(row.values()) for row in matrix_counts.values())
    diagonal = sum(matrix_counts[key][key] for key in category_keys)
    _require(total == validation["category_evaluable"], f"contract {area}: confusion total must be 184")
    _require(diagonal == validation["category"]["correct"], f"contract {area}: diagonal must be 171")

    derived_f1 = []
    per_class_keys = {"precision", "recall", "f1", "support"}
    for key in category_keys:
        metrics = per_class[key]
        _require(isinstance(metrics, dict), f"contract {area}: per-class {key!r} must be an object")
        _exact_keys(metrics, per_class_keys, f"{area} per-class {key}")
        support = sum(matrix_counts[key].values())
        predicted = sum(matrix_counts[actual][key] for actual in category_keys)
        true_positive = matrix_counts[key][key]
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        _require(
            _integer(metrics["support"], f"{area} per-class {key} support") == support,
            f"contract {area}: per-class support mismatch",
        )
        for field, value in (("precision", precision), ("recall", recall), ("f1", f1)):
            _rate(metrics[field], f"{area} per-class {key} {field}")
            _close(metrics[field], value, 1e-4, f"{area} per-class {key} {field} consistency")
        derived_f1.append(f1)
    _require(
        sum(_integer(item["support"], f"{area} support") for item in per_class.values())
        == validation["category_evaluable"],
        f"contract {area}: per-class supports must sum to 184",
    )
    _close(category.get("accuracy"), diagonal / total, 1e-4, f"{area} accuracy consistency")
    _close(category.get("macro_f1"), sum(derived_f1) / len(derived_f1), 1e-3, f"{area} macro-F1 consistency")


def _validate_ablation(root: Path, validation: dict) -> None:
    area = "ablation"
    rows = _read_csv(root, "validation/ablation.csv")
    keyed = _key_rows(rows, "ablation_id", area)
    expected_ids = {"remove_w1", "remove_w2", "remove_w3", "remove_w4"}
    _require(set(keyed) == expected_ids, f"contract {area}: IDs mismatch")
    for index in range(1, 5):
        row = keyed[f"remove_w{index}"]
        _require(row["removed_component"] == f"W{index}", f"contract {area}: component mismatch")
        _rate(row["recall"], f"{area} remove W{index} recall")
        _rate(row["f1"], f"{area} remove W{index} F1")
    locked = validation["ablation"]
    _close(keyed["remove_w3"]["recall"], locked["remove_w3_recall"], 1e-4, f"{area} W3 recall")
    _close(keyed["remove_w3"]["f1"], locked["remove_w3_f1"], 1e-4, f"{area} W3 F1")
    for component in ("w1", "w2", "w4"):
        _close(
            keyed[f"remove_{component}"]["f1"],
            locked["remove_w1_w2_w4_f1_approx"],
            locked["approx_tolerance"],
            f"{area} remove {component.upper()} approximate F1",
        )


def _validate_threshold_sweep(root: Path, validation: dict) -> None:
    area = "threshold sweep"
    rows = _read_csv(root, "validation/threshold_sweep.csv")
    keyed = {}
    for row in rows:
        threshold = _rate(row["threshold"], f"{area} threshold")
        _require(threshold not in keyed, f"contract {area}: duplicate threshold")
        keyed[threshold] = row
        for field in ("precision", "recall", "f1"):
            _rate(row[field], f"{area} {threshold:.2f} {field}")
        for field in ("candidate_count", "false_negative", "false_positive"):
            value = _integer(row[field], f"{area} {threshold:.2f} {field}")
            _require(value >= 0, f"contract {area}: {field} must be non-negative")
    locked = validation["threshold_sweep"]
    required = set(locked["required_thresholds"])
    _require(required <= set(keyed), f"contract {area}: missing required thresholds")
    _require(
        _integer(keyed[0.10]["candidate_count"], f"{area} 0.10 candidate_count")
        == locked["candidate_count_at_0_10"],
        f"contract {area}: 0.10 candidate_count must be 8950",
    )
    start_f1 = keyed[locked["plateau_start"]]["f1"]
    end_f1 = keyed[locked["plateau_end"]]["f1"]
    _close(start_f1, end_f1, locked["f1_plateau_tolerance"], f"{area} 0.05-0.10 F1 plateau")


def _validate_sportshare_cv(root: Path, validation: dict) -> None:
    area = "sportshare CV"
    payload = _read_json(root, "validation/sportshare_cv.json")
    locked = validation["sportshare"]
    for field in ("algorithm", "training_sample_count", "target"):
        _require(payload.get(field) == locked[field], f"contract {area}: {field} mismatch")
    feature_version = payload.get("feature_version")
    _require(
        isinstance(feature_version, str) and feature_version.strip(),
        f"contract {area}: feature_version must be non-empty",
    )
    _require(payload.get("cv") == locked["cv"], f"contract {area}: CV protocol mismatch")
    _require(payload.get("interval") == locked["interval"], f"contract {area}: interval mismatch")
    _require(
        payload.get("forbidden_features") == locked["forbidden_features"],
        f"contract {area}: forbidden_features mismatch",
    )
    q90 = _rate(payload.get("q90_abs_error"), f"{area} q90_abs_error")
    _require(0.0 <= q90 <= 1.0, f"contract {area}: q90_abs_error must be within [0, 1]")
    metrics = payload.get("metrics")
    _require(isinstance(metrics, dict), f"contract {area}: metrics required")
    _exact_keys(metrics, set(locked["metrics"]), f"{area} metrics")
    for field, locked_value in locked["metrics"].items():
        _close(metrics.get(field), locked_value, 1e-4, f"{area} {field}")


def _validate_benchmark(root: Path, validation: dict) -> None:
    area = "benchmark"
    payload = _read_json(root, "audit/benchmark.json")
    keys = {
        "status",
        "historical_single_run_seconds",
        "warmups",
        "repeats",
        "peak_memory_mb",
        "median_seconds",
        "mean_seconds",
        "std_seconds",
        "throughput_records_per_second",
        "raw_logs",
    }
    _exact_keys(payload, keys, area)
    locked = validation["benchmark"]
    _close(
        payload["historical_single_run_seconds"],
        locked["historical_single_run_seconds"],
        1e-9,
        f"{area} historical runtime",
    )
    for field in ("warmups", "repeats"):
        _require(payload[field] == locked[field], f"contract {area}: {field} mismatch")
    measurement_fields = (
        "peak_memory_mb",
        "median_seconds",
        "mean_seconds",
        "std_seconds",
        "throughput_records_per_second",
    )
    status = payload.get("status")
    _require(status in {"not_measured", "measured"}, f"contract {area}: invalid status")
    if status == "not_measured":
        _require(
            all(payload[field] is None for field in measurement_fields),
            f"contract {area}: not_measured numeric fields must be null",
        )
        _require(payload["raw_logs"] in (None, []), f"contract {area}: unmeasured raw_logs must be null/empty")
        return
    for field in measurement_fields:
        value = _number(payload[field], f"{area} measured {field}")
        _require(value >= 0.0, f"contract {area}: measured {field} must be non-negative")
    raw_logs = payload["raw_logs"]
    _require(
        isinstance(raw_logs, list)
        and bool(raw_logs)
        and all(isinstance(item, str) and item.strip() for item in raw_logs),
        f"contract {area}: measured raw_logs must be a non-empty string list",
    )


def _validate_metrics(root: Path, expected: dict) -> None:
    validation = expected["validation"]
    _validate_binary_metrics(root, validation)
    _validate_baselines(root, validation)
    _validate_category_metrics(root, expected)
    _validate_ablation(root, validation)
    _validate_threshold_sweep(root, validation)
    _validate_sportshare_cv(root, validation)
    _validate_benchmark(root, validation)


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
