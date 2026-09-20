"""Filesystem locations used by ATLAS. Never hard-code user-specific paths."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Atlas"


def get_app_data_dir() -> Path:
    """Return %APPDATA%\\Atlas, creating it if necessary."""
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    return get_app_data_dir() / "config.toml"


def get_log_dir() -> Path:
    path = get_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_plugins_dir() -> Path:
    path = get_app_data_dir() / "plugins"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_models_dir() -> Path:
    path = get_app_data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_known_folder(name: str) -> Path | None:
    """Resolve a well-known user folder (downloads, documents, desktop, pictures)."""
    home = Path.home()
    mapping = {
        "downloads": home / "Downloads",
        "documents": home / "Documents",
        "desktop": home / "Desktop",
        "pictures": home / "Pictures",
    }
    return mapping.get(name.lower())
