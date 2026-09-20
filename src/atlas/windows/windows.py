"""Window management abstraction (Atlas.md section 17), plus the pywin32
implementation. Commands must never touch Win32 directly - only through
this interface."""

from __future__ import annotations

import ctypes
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import win32api
import win32con
import win32gui
import win32process


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


def _process_path(pid: int) -> str:
    access = win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ
    try:
        handle = win32api.OpenProcess(access, False, pid)
    except Exception:  # noqa: BLE001 - a process we can't inspect just has no name
        return ""
    try:
        return win32process.GetModuleFileNameEx(handle, 0)
    except Exception:  # noqa: BLE001
        return ""
    finally:
        handle.Close()


class Win32WindowManager(WindowManager):
    def list_windows(self) -> list[WindowHandle]:
        results: list[WindowHandle] = []

        def _callback(hwnd: int, _: None) -> bool:
            if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process_name = os.path.basename(_process_path(pid))
            results.append(WindowHandle(handle=hwnd, title=title, process_name=process_name))
            return True

        win32gui.EnumWindows(_callback, None)
        return results

    def find_window(self, query: str) -> WindowHandle | None:
        query_lower = query.lower()
        for window in self.list_windows():
            if query_lower in window.title.lower() or query_lower in window.process_name.lower():
                return window
        return None

    def get_window_rect(self, window: WindowHandle) -> Rect:
        left, top, right, bottom = win32gui.GetWindowRect(window.handle)
        return Rect(x=left, y=top, width=right - left, height=bottom - top)

    def focus_window(self, window: WindowHandle) -> None:
        """Windows blocks a background process from stealing foreground
        focus outright; attaching to the current foreground thread's input
        queue for the duration of the call is the standard, side-effect-free
        way around that (as opposed to e.g. simulating an Alt keypress)."""
        if win32gui.IsIconic(window.handle):
            win32gui.ShowWindow(window.handle, win32con.SW_RESTORE)

        current_thread = win32api.GetCurrentThreadId()
        foreground_hwnd = win32gui.GetForegroundWindow()
        foreground_thread = (
            win32process.GetWindowThreadProcessId(foreground_hwnd)[0] if foreground_hwnd else 0
        )

        attached = False
        if foreground_thread and foreground_thread != current_thread:
            attached = bool(
                ctypes.windll.user32.AttachThreadInput(current_thread, foreground_thread, True)
            )
        try:
            win32gui.BringWindowToTop(window.handle)
            win32gui.SetForegroundWindow(window.handle)
        finally:
            if attached:
                ctypes.windll.user32.AttachThreadInput(current_thread, foreground_thread, False)

    def move_window(self, window: WindowHandle, rect: Rect) -> None:
        win32gui.MoveWindow(window.handle, rect.x, rect.y, rect.width, rect.height, True)

    def resize_window(self, window: WindowHandle, width: int, height: int) -> None:
        current = self.get_window_rect(window)
        win32gui.MoveWindow(window.handle, current.x, current.y, width, height, True)

    def maximize_window(self, window: WindowHandle) -> None:
        win32gui.ShowWindow(window.handle, win32con.SW_MAXIMIZE)

    def minimize_window(self, window: WindowHandle) -> None:
        win32gui.ShowWindow(window.handle, win32con.SW_MINIMIZE)

    def restore_window(self, window: WindowHandle) -> None:
        win32gui.ShowWindow(window.handle, win32con.SW_RESTORE)

    def close_window(self, window: WindowHandle) -> None:
        win32gui.PostMessage(window.handle, win32con.WM_CLOSE, 0, 0)
