"""Folder resolution for "open <folder>" (Atlas.md section 23). Never
allows arbitrary shell execution from voice input - the voice input only
ever supplies a lookup *key* into a trusted table (well-known OS folders,
or an admin-configured path), never a raw path, and the result is checked
to exist before anything is opened."""

from __future__ import annotations

from pathlib import Path

from atlas.config.schema import AtlasConfig
from atlas.utils.paths import get_known_folder


def resolve_folder(config: AtlasConfig | None, name: str) -> Path | None:
    key = name.strip().lower()

    if config is not None:
        configured = config.folders.get(key)
        if configured:
            path = Path(configured)
            if path.exists():
                return path

    known = get_known_folder(key)
    if known is not None and known.exists():
        return known

    return None
