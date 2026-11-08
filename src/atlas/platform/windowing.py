"""Window management interface (Atlas.md section 17). Commands only ever
talk to this; each OS backend implements it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class WindowHandle:
    handle: int
    title: str
    process_name: str
    process_path: str = ""


class WindowManager(ABC):
    @abstractmethod
    def list_windows(self) -> list[WindowHandle]: ...

    @abstractmethod
    def find_window(self, query: str) -> WindowHandle | None: ...

    @abstractmethod
    def get_window_rect(self, window: WindowHandle) -> Rect: ...

    @abstractmethod
    def focus_window(self, window: WindowHandle) -> None: ...

    @abstractmethod
    def move_window(self, window: WindowHandle, rect: Rect) -> None: ...

    @abstractmethod
    def resize_window(self, window: WindowHandle, width: int, height: int) -> None: ...

    @abstractmethod
    def maximize_window(self, window: WindowHandle) -> None: ...

    @abstractmethod
    def minimize_window(self, window: WindowHandle) -> None: ...

    @abstractmethod
    def restore_window(self, window: WindowHandle) -> None: ...

    @abstractmethod
    def close_window(self, window: WindowHandle) -> None: ...
