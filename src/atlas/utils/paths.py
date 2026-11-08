"""Filesystem locations used by ATLAS. Never hard-code user-specific paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Atlas"


def get_app_data_dir() -> Path:
    """The per-user data directory, created if necessary: %APPDATA%\\Atlas on
    Windows, ~/Library/Application Support/Atlas on macOS, and
    $XDG_DATA_HOME/Atlas (default ~/.local/share/Atlas) elsewhere."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME")
        root = Path(base) if base else Path.home() / ".local" / "share"
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
