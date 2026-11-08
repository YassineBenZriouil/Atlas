"""Merging discovered applications into config - shared by every
backend; scanning for them is the backend's job."""

from __future__ import annotations

import re
from dataclasses import dataclass

from atlas.config.schema import ApplicationEntry, AtlasConfig


@dataclass(frozen=True)
class DiscoveredApp:
    name: str
    target: str  # whatever the backend's ApplicationManager can launch


@dataclass(frozen=True)
class MergeResult:
    added: list[str]
    updated: list[str]


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def merge_discovered_apps(config: AtlasConfig, discovered: list[DiscoveredApp]) -> MergeResult:
    """Fills in a real launch target for any already-configured app
    (matched by key or by an existing alias) that has no executable yet,
    and adds a new entry for everything else discovered. Never overwrites
    an executable that's already set, so a user's own hand-picked path -
    or an earlier discovery run - always wins; this can be re-run safely
    any time new software is installed."""
    alias_to_key: dict[str, str] = {}
    for key, entry in config.applications.items():
        alias_to_key[key.lower()] = key
        for alias in entry.aliases:
            alias_to_key[alias.lower()] = key

    added: list[str] = []
    updated: list[str] = []

    for app in discovered:
        name_lower = app.name.lower()
        existing_key = alias_to_key.get(name_lower)
        if existing_key is not None:
            entry = config.applications[existing_key]
            if not entry.executable:
                entry.executable = app.target
                updated.append(app.name)
            continue

        slug = _slugify(app.name)
        if not slug or slug in config.applications:
            continue

        config.applications[slug] = ApplicationEntry(executable=app.target, aliases=[name_lower])
        alias_to_key[name_lower] = slug
        added.append(app.name)

    return MergeResult(added=added, updated=updated)
