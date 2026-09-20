"""Monitor management abstraction (Atlas.md section 20), plus the Win32
implementation - enumeration is read-only, so there is no interface/
implementation split needed for testability the way there is for windows."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import win32api

from atlas.windows.windows import Rect


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


def _rect_from_win32(bounds: tuple[int, int, int, int]) -> Rect:
    left, top, right, bottom = bounds
    return Rect(x=left, y=top, width=right - left, height=bottom - top)


class Win32MonitorManager(MonitorManager):
    """Monitor numbering (1-based) matches the order Windows itself
    enumerates displays in, which is what a user means by "monitor two"."""

    def list_monitors(self) -> list[Monitor]:
        monitors: list[Monitor] = []
        for index, (handle, _, _) in enumerate(win32api.EnumDisplayMonitors(), start=1):
            info = win32api.GetMonitorInfo(handle)
            monitors.append(
                Monitor(
                    index=index,
                    name=info["Device"],
                    bounds=_rect_from_win32(info["Monitor"]),
                    work_area=_rect_from_win32(info["Work"]),
                    is_primary=bool(info["Flags"] & 1),
                )
            )
        return monitors

    def get_primary_monitor(self) -> Monitor:
        for monitor in self.list_monitors():
            if monitor.is_primary:
                return monitor
        raise RuntimeError("No primary monitor detected")

    def get_monitor(self, number: int) -> Monitor | None:
        for monitor in self.list_monitors():
            if monitor.index == number:
                return monitor
        return None
