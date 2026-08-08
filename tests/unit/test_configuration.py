from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from backend.core import configuration
from backend.core.configuration import (
    ConfigurationError,
    ConfigurationHashMismatch,
    ConfigurationNotFound,
    ConfigurationParseError,
    ConfigurationVersionError,
    FormalConfigurationUnavailable,
    load_config,
    require_formal_config,
    sha256_file,
)


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_yaml(path: Path, payload: object) -> Path:
    return write(path, yaml.safe_dump(payload, allow_unicode=True, sort_keys=False))


def valid_config_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "config_id": "SPORT-SCORE-CONFIG",
        "version": "V1",
        "status": "ready",
        "source": "report_alignment_migration",
    }
    payload.update(overrides)
    return payload


def prepare_formal_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    entry_overrides: dict[str, object] | None = None,
) -> Path:
    config_path = write_yaml(
        tmp_path / "config" / "sportscore.yaml", valid_config_payload()
    )
    entry: dict[str, object] = {
        "config_id": "SPORT-SCORE-CONFIG",
        "path": "config/sportscore.yaml",
        "version": "V1",
        "status": "ready",
        "sha256": sha256_file(config_path),
    }
    entry.update(entry_overrides or {})
    manifest_path = write_yaml(
        tmp_path / "config" / "manifest.yaml",
        {
            "schema_version": 1,
            "config_id": "CONFIG-MANIFEST",
            "version": "PHASE0",
            "status": "ready",
            "source": "phase0_safety_net",
            "configs": [entry],
        },
    )
    monkeypatch.setattr(configuration, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(configuration, "MANIFEST_PATH", manifest_path)
    return config_path


def test_sha256_file_hashes_original_bytes(tmp_path):
    path = tmp_path / "sample.yaml"
    payload = (
        "schema_version: 1\nconfig_id: SAMPLE\nversion: V1\nstatus: ready\n"
        "source: unit_test\n"
    )
    path.write_bytes(payload.encode("utf-8"))
    assert sha256_file(path) == sha256(payload.encode("utf-8")).hexdigest()


def test_load_config_rejects_invalid_yaml(tmp_path):
    path = write(tmp_path / "broken.yaml", "schema_version: [\n")
    with pytest.raises(ConfigurationParseError, match="broken.yaml"):
        load_config(path)


def test_load_config_distinguishes_missing_file(tmp_path):
    with pytest.raises(ConfigurationNotFound, match="missing.yaml"):
        load_config(tmp_path / "missing.yaml")


def test_load_config_rejects_empty_version(tmp_path):
    path = write_yaml(tmp_path / "empty-version.yaml", valid_config_payload(version=""))
    with pytest.raises(ConfigurationVersionError, match="version"):
        load_config(path)


@pytest.mark.parametrize(
    "schema_version",
    (None, 2, "1", True),
)
def test_load_config_rejects_missing_or_incompatible_schema_version(
    tmp_path, schema_version
):
    payload = valid_config_payload()
    if schema_version is None:
        payload.pop("schema_version")
    else:
        payload["schema_version"] = schema_version
    path = write_yaml(tmp_path / "schema-version.yaml", payload)
    with pytest.raises(
        ConfigurationVersionError, match=r"schema-version\.yaml.*schema_version"
    ):
        load_config(path)


@pytest.mark.parametrize("field", ("config_id", "version", "status", "source"))
def test_load_config_rejects_missing_required_string_fields(tmp_path, field):
    payload = valid_config_payload()
    payload.pop(field)
    path = write_yaml(tmp_path / f"missing-{field}.yaml", payload)
    with pytest.raises(ConfigurationParseError, match=field):
        load_config(path)


@pytest.mark.parametrize("field", ("config_id", "version", "status", "source"))
@pytest.mark.parametrize("invalid_value", ("", "   ", True, 1, ["value"], None))
def test_load_config_rejects_empty_or_non_string_required_fields(
    tmp_path, field, invalid_value
):
    path = write_yaml(
        tmp_path / f"invalid-{field}.yaml",
        valid_config_payload(**{field: invalid_value}),
    )
    with pytest.raises(ConfigurationError, match=field):
        load_config(path)


def test_require_formal_config_rejects_not_imported(tmp_path):
    path = write_yaml(
        tmp_path / "sportshare.yaml",
        valid_config_payload(
            config_id="SPORT-SHARE-CONFIG",
            version="NOT-IMPORTED",
            status="not_imported",
        ),
    )
    with pytest.raises(FormalConfigurationUnavailable, match="not_imported"):
        require_formal_config(path)


def test_require_formal_config_rejects_hash_mismatch(tmp_path, monkeypatch):
    path = prepare_formal_config(
        tmp_path,
        monkeypatch,
        entry_overrides={"sha256": "0" * 64},
    )
    with pytest.raises(ConfigurationHashMismatch, match="SPORT-SCORE-CONFIG"):
        require_formal_config(path)


def test_require_formal_config_returns_path_bound_verified_config(
    tmp_path, monkeypatch
):
    path = prepare_formal_config(tmp_path, monkeypatch)

    assert require_formal_config(path)["version"] == "V1"


def test_require_formal_config_accepts_uppercase_sha256(tmp_path, monkeypatch):
    path = prepare_formal_config(tmp_path, monkeypatch)
    manifest = yaml.safe_load(configuration.MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["configs"][0]["sha256"] = manifest["configs"][0]["sha256"].upper()
    write_yaml(configuration.MANIFEST_PATH, manifest)

    assert require_formal_config(path)["version"] == "V1"


def test_require_formal_config_rejects_resolved_path_outside_project_root(
    tmp_path, monkeypatch
):
    path = prepare_formal_config(tmp_path, monkeypatch)
    original_resolve = Path.resolve
    escaped_path = tmp_path.parent / "outside" / "sportscore.yaml"

    def fake_resolve(candidate: Path, *args, **kwargs):
        if candidate == path:
            return escaped_path
        return original_resolve(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    with pytest.raises(FormalConfigurationUnavailable, match="project root"):
        require_formal_config(path)


def test_require_formal_config_rejects_project_root_as_resolved_config_path(
    tmp_path, monkeypatch
):
    path = prepare_formal_config(tmp_path, monkeypatch)
    original_resolve = Path.resolve

    def fake_resolve(candidate: Path, *args, **kwargs):
        if candidate == path:
            return tmp_path
        return original_resolve(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    with pytest.raises(FormalConfigurationUnavailable, match="project root"):
        require_formal_config(path)


def test_require_formal_config_fails_closed_when_containment_check_errors(
    tmp_path, monkeypatch
):
    path = prepare_formal_config(tmp_path, monkeypatch)
    original_is_relative_to = Path.is_relative_to

    def failing_is_relative_to(candidate: Path, other: Path):
        if candidate == path:
            raise ValueError("different drive")
        return original_is_relative_to(candidate, other)

    monkeypatch.setattr(Path, "is_relative_to", failing_is_relative_to)

    with pytest.raises(FormalConfigurationUnavailable, match="project root"):
        require_formal_config(path)


def test_require_formal_config_rejects_same_content_at_unregistered_path(
    tmp_path, monkeypatch
):
    registered_path = prepare_formal_config(tmp_path, monkeypatch)
    copied_path = tmp_path / "copied-sportscore.yaml"
    copied_path.write_bytes(registered_path.read_bytes())

    with pytest.raises(FormalConfigurationUnavailable, match="path"):
        require_formal_config(copied_path)


def test_require_formal_config_rejects_manifest_path_mismatch(tmp_path, monkeypatch):
    path = prepare_formal_config(
        tmp_path,
        monkeypatch,
        entry_overrides={"path": "config/other.yaml"},
    )

    with pytest.raises(FormalConfigurationUnavailable, match="path"):
        require_formal_config(path)


@pytest.mark.parametrize(
    "unsafe_path",
    (
        "",
        None,
        123,
        "/config/sportscore.yaml",
        "C:/project/config/sportscore.yaml",
        r"C:\project\config\sportscore.yaml",
        r"config\sportscore.yaml",
        "./config/sportscore.yaml",
        "config/./sportscore.yaml",
        "config/../sportscore.yaml",
        "config//sportscore.yaml",
        "config/",
    ),
)
def test_require_formal_config_rejects_unsafe_manifest_paths(
    tmp_path, monkeypatch, unsafe_path
):
    path = prepare_formal_config(
        tmp_path,
        monkeypatch,
        entry_overrides={"path": unsafe_path},
    )

    with pytest.raises(FormalConfigurationUnavailable, match="path"):
        require_formal_config(path)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (
        ("config_id", 123),
        ("config_id", ""),
        ("version", 1),
        ("version", ""),
        ("status", True),
        ("status", ""),
        ("sha256", 123),
        ("sha256", "deadbeef"),
        ("sha256", "g" * 64),
    ),
)
def test_require_formal_config_rejects_invalid_manifest_entry_types(
    tmp_path, monkeypatch, field, invalid_value
):
    path = prepare_formal_config(
        tmp_path,
        monkeypatch,
        entry_overrides={field: invalid_value},
    )

    with pytest.raises(FormalConfigurationUnavailable, match=field):
        require_formal_config(path)


@pytest.mark.parametrize(
    ("field", "mismatched_value"),
    (("version", "V2"), ("status", "draft")),
)
def test_require_formal_config_rejects_manifest_metadata_mismatch(
    tmp_path, monkeypatch, field, mismatched_value
):
    path = prepare_formal_config(
        tmp_path,
        monkeypatch,
        entry_overrides={field: mismatched_value},
    )

    with pytest.raises(FormalConfigurationUnavailable, match=field):
        require_formal_config(path)
