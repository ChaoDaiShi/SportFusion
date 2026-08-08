from hashlib import sha256
from pathlib import Path

import pytest

from backend.core import configuration
from backend.core.configuration import (
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
    path.write_text(content, encoding="utf-8")
    return path


def test_sha256_file_hashes_original_bytes(tmp_path):
    path = tmp_path / "sample.yaml"
    payload = "schema_version: 1\nconfig_id: SAMPLE\nversion: V1\nstatus: ready\n"
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
    path = write(
        tmp_path / "empty-version.yaml",
        "schema_version: 1\nconfig_id: SAMPLE\nversion: ''\nstatus: ready\n",
    )
    with pytest.raises(ConfigurationVersionError, match="version"):
        load_config(path)


def test_require_formal_config_rejects_not_imported(tmp_path):
    path = write(
        tmp_path / "sportshare.yaml",
        "schema_version: 1\nconfig_id: SPORT-SHARE-CONFIG\n"
        "version: NOT-IMPORTED\nstatus: not_imported\n",
    )
    with pytest.raises(FormalConfigurationUnavailable, match="not_imported"):
        require_formal_config(path)


def test_require_formal_config_rejects_hash_mismatch(tmp_path, monkeypatch):
    path = write(
        tmp_path / "sportscore.yaml",
        "schema_version: 1\nconfig_id: SPORT-SCORE-CONFIG\nversion: V1\nstatus: ready\n",
    )
    manifest = write(
        tmp_path / "manifest.yaml",
        "schema_version: 1\nconfig_id: CONFIG-MANIFEST\nversion: PHASE0\nstatus: ready\n"
        "configs:\n  - config_id: SPORT-SCORE-CONFIG\n    path: config/sportscore.yaml\n"
        "    version: V1\n    status: ready\n    sha256: deadbeef\n",
    )
    monkeypatch.setattr(configuration, "MANIFEST_PATH", manifest)
    with pytest.raises(ConfigurationHashMismatch, match="SPORT-SCORE-CONFIG"):
        require_formal_config(path)


def test_require_formal_config_returns_verified_config(tmp_path, monkeypatch):
    path = write(
        tmp_path / "sportscore.yaml",
        "schema_version: 1\nconfig_id: SPORT-SCORE-CONFIG\nversion: V1\nstatus: ready\n",
    )
    digest = sha256_file(path)
    manifest = write(
        tmp_path / "manifest.yaml",
        "schema_version: 1\nconfig_id: CONFIG-MANIFEST\nversion: PHASE0\nstatus: ready\n"
        "configs:\n  - config_id: SPORT-SCORE-CONFIG\n    path: config/sportscore.yaml\n"
        f"    version: V1\n    status: ready\n    sha256: {digest}\n",
    )
    monkeypatch.setattr(configuration, "MANIFEST_PATH", manifest)
    assert require_formal_config(path)["version"] == "V1"
