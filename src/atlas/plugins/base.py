"""Plugin interface every ATLAS plugin must implement (Atlas.md section 43)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from atlas.commands.registry import CommandRegistry


@dataclass
class PluginContext:
    config: Any = None
    extra: dict[str, Any] = field(default_factory=dict)


class AtlasPlugin(ABC):
    name: str = ""

    @abstractmethod
    def initialize(self, context: PluginContext) -> None: ...

    @abstractmethod
    def register_commands(self, registry: CommandRegistry) -> None: ...

    @abstractmethod
    def shutdown(self) -> None: ...
