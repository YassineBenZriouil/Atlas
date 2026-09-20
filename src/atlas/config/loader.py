"""Load/save TOML configuration with schema migration (Atlas.md section 64)."""

from __future__ import annotations

import tomllib
import typing
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any

import tomli_w

from atlas.config.defaults import default_config
from atlas.config.schema import CURRENT_CONFIG_VERSION, AtlasConfig


class ConfigError(RuntimeError):
    pass


def _dataclass_from_dict(cls: type, data: dict[str, Any]) -> Any:
    hints = typing.get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for f in fields(cls):
        if f.name not in data:
            continue
        value = data[f.name]
        field_type = hints.get(f.name)
        if isinstance(field_type, type) and is_dataclass(field_type) and isinstance(value, dict):
            kwargs[f.name] = _dataclass_from_dict(field_type, value)
        else:
            kwargs[f.name] = value
    return cls(**kwargs)


def _migrate(raw: dict[str, Any]) -> dict[str, Any]:
    version = raw.get("config_version", 1)
    if version > CURRENT_CONFIG_VERSION:
        raise ConfigError(
            f"Configuration version {version} is newer than supported "
            f"({CURRENT_CONFIG_VERSION}). Refusing to load."
        )
    # Future migrations go here, e.g.:
    # if version < 2: raw = _migrate_v1_to_v2(raw)
    raw["config_version"] = CURRENT_CONFIG_VERSION
    return raw


def load_config(path: Path) -> AtlasConfig:
    if not path.exists():
        config = default_config()
        save_config(path, config)
        return config

    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ConfigError(f"Failed to read configuration at {path}: {exc}") from exc

    raw = _migrate(raw)

    from atlas.config.schema import ApplicationEntry

    applications = {
        name: ApplicationEntry(**entry) for name, entry in raw.get("applications", {}).items()
    }

    try:
        config = _dataclass_from_dict(AtlasConfig, raw)
    except TypeError as exc:
        raise ConfigError(f"Malformed configuration at {path}: {exc}") from exc

    config.applications = applications
    return config


def save_config(path: Path, config: AtlasConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(config)
    try:
        serialized = tomli_w.dumps(data)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Failed to serialize configuration: {exc}") from exc
    path.write_text(serialized, encoding="utf-8")
