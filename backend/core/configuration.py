from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from .versions import CONFIG_SCHEMA_VERSION, FORMAL_READY_STATUS, NOT_IMPORTED_VERSION

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "config" / "manifest.yaml"
REQUIRED_FIELDS = ("config_id", "version", "status")


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
            f"配置 {path.name} 的 schema_version 必须为 {CONFIG_SCHEMA_VERSION}，当前为 {schema_version!r}"
        )
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ConfigurationParseError(f"配置 {path.name} 缺少字段: {', '.join(missing)}")
    if not isinstance(payload["version"], str) or not payload["version"].strip():
        raise ConfigurationVersionError(f"配置 {path.name} 的 version 不能为空")
    return payload


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
    entry = next(
        (item for item in manifest.get("configs", []) if item.get("config_id") == payload["config_id"]),
        None,
    )
    if not entry or not entry.get("sha256"):
        raise FormalConfigurationUnavailable(
            f"配置 {payload['config_id']} 未在 manifest 中登记有效 SHA256"
        )
    if entry.get("status") != FORMAL_READY_STATUS or entry.get("version") != version:
        raise FormalConfigurationUnavailable(
            f"配置 {payload['config_id']} 与 manifest 的 status/version 不一致"
        )
    actual = sha256_file(path)
    expected = entry["sha256"]
    if actual != expected:
        raise ConfigurationHashMismatch(
            f"配置 {payload['config_id']} SHA256 不一致: expected={expected}, actual={actual}"
        )
    return payload
