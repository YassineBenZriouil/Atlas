"""Monitor enumeration interface (Atlas.md section 20)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from atlas.platform.windowing import Rect


@dataclass(frozen=True)
class Monitor:
    index: int
    name: str
    bounds: Rect
    work_area: Rect
    is_primary: bool


class MonitorManager(ABC):
    @abstractmethod
    def list_monitors(self) -> list[Monitor]: ...

    @abstractmethod
    def get_primary_monitor(self) -> Monitor: ...

    @abstractmethod
    def get_monitor(self, number: int) -> Monitor | None: ...
