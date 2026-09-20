"""Mouse automation abstraction (Atlas.md section 25), plus the Win32
implementation. Absolute-coordinate voice commands are explicitly out of
scope for the initial release."""

from __future__ import annotations

from abc import ABC, abstractmethod

import win32api
import win32con


class MouseController(ABC):
    @abstractmethod
    def click(self) -> None: ...

    @abstractmethod
    def double_click(self) -> None: ...

    @abstractmethod
    def right_click(self) -> None: ...

    @abstractmethod
    def move_relative(self, dx: int, dy: int) -> None: ...

    @abstractmethod
    def scroll(self, amount: int) -> None: ...


class Win32MouseController(MouseController):
    def click(self) -> None:
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def double_click(self) -> None:
        self.click()
        self.click()

    def right_click(self) -> None:
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def move_relative(self, dx: int, dy: int) -> None:
        x, y = win32api.GetCursorPos()
        win32api.SetCursorPos((x + dx, y + dy))

    def scroll(self, amount: int) -> None:
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount * 120, 0)
