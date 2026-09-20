"""Tracks which plugins are loaded vs. disabled, and why (Atlas.md section 44)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from atlas.plugins.base import AtlasPlugin


class PluginStatus(Enum):
    LOADED = auto()
    DISABLED = auto()


@dataclass
class PluginRecord:
    name: str
    status: PluginStatus
    reason: str = ""
    instance: AtlasPlugin | None = None


class PluginRegistry:
    def __init__(self) -> None:
        self._records: dict[str, PluginRecord] = {}

    def mark_loaded(self, plugin: AtlasPlugin) -> None:
        self._records[plugin.name] = PluginRecord(
            plugin.name, PluginStatus.LOADED, instance=plugin
        )

    def mark_disabled(self, name: str, reason: str) -> None:
        self._records[name] = PluginRecord(name, PluginStatus.DISABLED, reason=reason)

    def get(self, name: str) -> PluginRecord | None:
        return self._records.get(name)

    def all(self) -> list[PluginRecord]:
        return list(self._records.values())

    def loaded_plugins(self) -> list[AtlasPlugin]:
        return [
            record.instance
            for record in self._records.values()
            if record.status == PluginStatus.LOADED and record.instance is not None
        ]
