"""Load/save TOML configuration with schema migration (Atlas.md section 64)."""

from __future__ import annotations

import tomllib
import typing
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any

import tomli_w

from atlas.config.defaults import default_config
from atlas.config.schema import CURRENT_CONFIG_VERSION, AtlasConfig, SpeechConfig


class ConfigError(RuntimeError):
    pass


def _check_type(name: str, value: Any, field_type: Any) -> None:
    if field_type is float:
        ok = isinstance(value, int | float) and not isinstance(value, bool)
    elif field_type is int:
        ok = isinstance(value, int) and not isinstance(value, bool)
    else:
        origin = typing.get_origin(field_type) or field_type
        ok = not isinstance(origin, type) or isinstance(
            value, dict if is_dataclass(origin) else origin
        )
    if not ok:
        raise TypeError(f"'{name}' has the wrong type ({type(value).__name__})")


def _dataclass_from_dict(cls: type, data: dict[str, Any]) -> Any:
    hints = typing.get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for f in fields(cls):
        if f.name not in data:
            continue
        value = data[f.name]
        field_type = hints.get(f.name)
        _check_type(f.name, value, field_type)
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
    if version < 2:
        # v1 always saved engine = "vosk" (the only engine then); v2 adds the
        # Windows recognizer and makes it the default on Windows.
        speech = raw.setdefault("speech", {})
        if isinstance(speech, dict) and speech.get("engine", "vosk") == "vosk":
            speech["engine"] = SpeechConfig().engine
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

    try:
        return config_from_dict(raw)
    except ConfigError as exc:
        raise ConfigError(f"Malformed configuration at {path}: {exc}") from exc


def config_from_dict(raw: dict[str, Any]) -> AtlasConfig:
    """Build a config from TOML-shaped data (a loaded file, or the core
    service's config API). Raises ConfigError on malformed input."""
    raw = _migrate(dict(raw))

    from atlas.config.schema import ApplicationEntry

    try:
        applications = {
            name: ApplicationEntry(**entry) for name, entry in raw.get("applications", {}).items()
        }
        config = _dataclass_from_dict(AtlasConfig, raw)
    except (TypeError, AttributeError) as exc:
        raise ConfigError(str(exc)) from exc

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
