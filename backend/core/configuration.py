import re
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from .versions import CONFIG_SCHEMA_VERSION, FORMAL_READY_STATUS, NOT_IMPORTED_VERSION

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "config" / "manifest.yaml"
REQUIRED_FIELDS = ("config_id", "version", "status", "source")
MANIFEST_ENTRY_FIELDS = ("config_id", "path", "version", "status", "sha256")
SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}\Z")
WINDOWS_DRIVE_PATTERN = re.compile(r"[A-Za-z]:")


class ConfigurationError(RuntimeError):
    pass


class ConfigurationParseError(ConfigurationError):
    pass


class ConfigurationNotFound(ConfigurationError):
    pass


class ConfigurationVersionError(ConfigurationError):
    pass


class ConfigurationHashMismatch(ConfigurationError):
    pass


class FormalConfigurationUnavailable(ConfigurationError):
    pass


def sha256_file(path: Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _require_nonempty_string(payload: dict[str, Any], field: str, path: Path) -> None:
    value = payload[field]
    if isinstance(value, str) and value.strip():
        return
    error_type = ConfigurationVersionError if field == "version" else ConfigurationParseError
    raise error_type(f"Configuration {path.name} field {field} must be a non-empty string")


def load_config(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationNotFound(f"配置文件不存在: {path.name}") from exc
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationParseError(f"无法读取配置 {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationParseError(f"配置 {path.name} 的根节点必须是映射")
    schema_version = payload.get("schema_version")
    if type(schema_version) is not int or schema_version != CONFIG_SCHEMA_VERSION:
        raise ConfigurationVersionError(
            f"配置 {path.name} 的 schema_version 必须为 {CONFIG_SCHEMA_VERSION}，"
            f"当前为 {schema_version!r}"
        )
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ConfigurationParseError(
            f"Configuration {path.name} missing fields: {', '.join(missing)}"
        )
    for field in REQUIRED_FIELDS:
        _require_nonempty_string(payload, field, path)
    return payload


def _manifest_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    configs = manifest.get("configs")
    if not isinstance(configs, list):
        raise FormalConfigurationUnavailable("Manifest field configs must be a list")

    entries: list[dict[str, Any]] = []
    for item in configs:
        if not isinstance(item, dict):
            raise FormalConfigurationUnavailable("Manifest config entry must be a mapping")
        config_id = item.get("config_id")
        if not isinstance(config_id, str) or not config_id.strip():
            raise FormalConfigurationUnavailable(
                "Manifest entry config_id must be a non-empty string"
            )
        entries.append(item)
    return entries


def _manifest_entry_for(
    manifest: dict[str, Any], config_id: str
) -> dict[str, Any]:
    matches = [
        entry for entry in _manifest_entries(manifest) if entry["config_id"] == config_id
    ]
    if len(matches) != 1:
        raise FormalConfigurationUnavailable(
            f"Manifest must contain exactly one config_id entry for {config_id}"
        )
    return matches[0]


def _validate_manifest_entry(entry: dict[str, Any]) -> list[str]:
    missing = [field for field in MANIFEST_ENTRY_FIELDS if field not in entry]
    if missing:
        raise FormalConfigurationUnavailable(
            f"Manifest entry missing fields: {', '.join(missing)}"
        )

    for field in ("config_id", "version", "status"):
        value = entry[field]
        if not isinstance(value, str) or not value.strip():
            raise FormalConfigurationUnavailable(
                f"Manifest entry {field} must be a non-empty string"
            )

    manifest_path = entry["path"]
    if not isinstance(manifest_path, str) or not manifest_path.strip():
        raise FormalConfigurationUnavailable(
            "Manifest entry path must be a non-empty POSIX relative path"
        )
    if "\\" in manifest_path or WINDOWS_DRIVE_PATTERN.match(manifest_path):
        raise FormalConfigurationUnavailable(
            "Manifest entry path must be a POSIX project-relative path"
        )
    path_parts = manifest_path.split("/")
    if manifest_path.startswith("/") or any(
        part in {"", ".", ".."} for part in path_parts
    ):
        raise FormalConfigurationUnavailable(
            "Manifest entry path must not be absolute or contain empty/dot segments"
        )

    expected_hash = entry["sha256"]
    if not isinstance(expected_hash, str) or not SHA256_PATTERN.fullmatch(expected_hash):
        raise FormalConfigurationUnavailable(
            "Manifest entry sha256 must contain exactly 64 hexadecimal characters"
        )
    return path_parts


def require_formal_config(path: Path) -> dict[str, Any]:
    path = Path(path)
    payload = load_config(path)
    status = payload["status"]
    version = payload["version"]
    if status != FORMAL_READY_STATUS or version == NOT_IMPORTED_VERSION:
        raise FormalConfigurationUnavailable(
            f"配置 {path.name} 当前状态为 {status}，版本为 {version}，不能用于 formal 模式"
        )

    manifest = load_config(MANIFEST_PATH)
    entry = _manifest_entry_for(manifest, payload["config_id"])
    path_parts = _validate_manifest_entry(entry)

    if entry["status"] != status:
        raise FormalConfigurationUnavailable(
            f"Configuration {payload['config_id']} status differs from manifest status"
        )
    if entry["version"] != version:
        raise FormalConfigurationUnavailable(
            f"Configuration {payload['config_id']} version differs from manifest version"
        )

    project_root = Path(PROJECT_ROOT).resolve()
    registered_path = project_root.joinpath(*path_parts).resolve()
    supplied_path = path.resolve()
    try:
        registered_path_is_contained = (
            registered_path != project_root
            and registered_path.is_relative_to(project_root)
        )
    except (OSError, ValueError):
        registered_path_is_contained = False
    if not registered_path_is_contained:
        raise FormalConfigurationUnavailable(
            f"Configuration {payload['config_id']} path escapes the project root"
        )
    if registered_path != supplied_path:
        raise FormalConfigurationUnavailable(
            f"Configuration {payload['config_id']} path differs from manifest path"
        )

    actual = sha256_file(path)
    expected = entry["sha256"].lower()
    if actual != expected:
        raise ConfigurationHashMismatch(
            f"配置 {payload['config_id']} SHA256 不一致: expected={expected}, actual={actual}"
        )
    return payload
