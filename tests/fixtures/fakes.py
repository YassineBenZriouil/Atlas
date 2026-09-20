"""In-memory fakes for the Windows abstraction layer, so command and
Application-level logic can be exercised deterministically without
touching real Win32 APIs (and, critically, without ever actually shutting
down/restarting the machine when testing the confirmation flow)."""

from __future__ import annotations

from atlas.windows.applications import ApplicationInfo, ApplicationManager, ApplicationNotFoundError
from atlas.windows.keyboard import KeyboardController, key_to_vk
from atlas.windows.monitors import Monitor, MonitorManager
from atlas.windows.mouse import MouseController
from atlas.windows.system import SystemController
from atlas.windows.windows import Rect, WindowHandle, WindowManager


class FakeWindowManager(WindowManager):
    def __init__(self) -> None:
        self.windows: dict[int, WindowHandle] = {}
        self.rects: dict[int, Rect] = {}
        self.calls: list[tuple] = []
        self._next_handle = 1

    def add_window(
        self, title: str, process_name: str, rect: Rect | None = None
    ) -> WindowHandle:
        handle = WindowHandle(handle=self._next_handle, title=title, process_name=process_name)
        self._next_handle += 1
        self.windows[handle.handle] = handle
        self.rects[handle.handle] = rect or Rect(0, 0, 800, 600)
        return handle

    def list_windows(self) -> list[WindowHandle]:
        return list(self.windows.values())

    def find_window(self, query: str) -> WindowHandle | None:
        q = query.lower()
        for window in self.windows.values():
            if q in window.title.lower() or q in window.process_name.lower():
                return window
        return None

    def get_window_rect(self, window: WindowHandle) -> Rect:
        return self.rects[window.handle]

    def focus_window(self, window: WindowHandle) -> None:
        self.calls.append(("focus", window))

    def move_window(self, window: WindowHandle, rect: Rect) -> None:
        self.rects[window.handle] = rect
        self.calls.append(("move", window, rect))

    def resize_window(self, window: WindowHandle, width: int, height: int) -> None:
        current = self.rects[window.handle]
        self.rects[window.handle] = Rect(current.x, current.y, width, height)
        self.calls.append(("resize", window, width, height))

    def maximize_window(self, window: WindowHandle) -> None:
        self.calls.append(("maximize", window))

    def minimize_window(self, window: WindowHandle) -> None:
        self.calls.append(("minimize", window))

    def restore_window(self, window: WindowHandle) -> None:
        self.calls.append(("restore", window))

    def close_window(self, window: WindowHandle) -> None:
        self.windows.pop(window.handle, None)
        self.calls.append(("close", window))


class FakeApplicationManager(ApplicationManager):
    def __init__(self, window_manager: FakeWindowManager) -> None:
        self._window_manager = window_manager
        self.running: dict[str, WindowHandle] = {}
        self.launched: list[str] = []

    def resolve_alias(self, alias: str) -> ApplicationInfo | None:
        return ApplicationInfo(alias=alias.lower(), executable_path=None)

    def locate(self, alias: str) -> str | None:
        return None if alias == "unknownapp" else f"C:/fake/{alias}.exe"

    def launch(self, alias: str) -> None:
        if alias == "unknownapp":
            raise ApplicationNotFoundError(alias)
        self.launched.append(alias)
        window = self._window_manager.add_window(title=alias, process_name=f"{alias}.exe")
        self.running[alias.lower()] = window

    def terminate(self, alias: str) -> None:
        window = self.running.pop(alias.lower(), None)
        if window is not None:
            self._window_manager.close_window(window)

    def is_running(self, alias: str) -> bool:
        return alias.lower() in self.running

    def windows_for(self, alias: str) -> list[WindowHandle]:
        window = self.running.get(alias.lower())
        return [window] if window is not None else []


class FakeMonitorManager(MonitorManager):
    def __init__(self, monitors: list[Monitor] | None = None) -> None:
        self.monitors = monitors or [
            Monitor(1, "PRIMARY", Rect(0, 0, 1920, 1080), Rect(0, 0, 1920, 1040), True),
            Monitor(2, "SECONDARY", Rect(1920, 0, 1280, 1024), Rect(1920, 0, 1280, 984), False),
        ]

    def list_monitors(self) -> list[Monitor]:
        return list(self.monitors)

    def get_primary_monitor(self) -> Monitor:
        return next(m for m in self.monitors if m.is_primary)

    def get_monitor(self, number: int) -> Monitor | None:
        return next((m for m in self.monitors if m.index == number), None)


class FakeKeyboardController(KeyboardController):
    """Still validates keys via the real key_to_vk table, so a test using
    an unmappable key fails the same way the real controller would."""

    def __init__(self) -> None:
        self.pressed: list[str] = []
        self.combos: list[list[str]] = []

    def press_key(self, key: str) -> None:
        key_to_vk(key)
        self.pressed.append(key)

    def press_combo(self, keys: list[str]) -> None:
        for key in keys:
            key_to_vk(key)
        self.combos.append(list(keys))


class FakeMouseController(MouseController):
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def click(self) -> None:
        self.calls.append(("click",))

    def double_click(self) -> None:
        self.calls.append(("double_click",))

    def right_click(self) -> None:
        self.calls.append(("right_click",))

    def move_relative(self, dx: int, dy: int) -> None:
        self.calls.append(("move_relative", dx, dy))

    def scroll(self, amount: int) -> None:
        self.calls.append(("scroll", amount))


class FakeSystemController(SystemController):
    def __init__(self) -> None:
        self.muted = False
        self.volume = 50
        self.calls: list[tuple] = []
        self.shutdown_called = False
        self.restart_called = False

    def mute(self) -> None:
        self.muted = True
        self.calls.append(("mute",))

    def unmute(self) -> None:
        self.muted = False
        self.calls.append(("unmute",))

    def set_volume(self, level: int) -> None:
        self.volume = level
        self.calls.append(("set_volume", level))

    def volume_up(self, step: int = 10) -> None:
        self.volume = min(100, self.volume + step)
        self.calls.append(("volume_up", step))

    def volume_down(self, step: int = 10) -> None:
        self.volume = max(0, self.volume - step)
        self.calls.append(("volume_down", step))

    def lock(self) -> None:
        self.calls.append(("lock",))

    def sleep(self) -> None:
        self.calls.append(("sleep",))

    def shutdown(self) -> None:
        self.shutdown_called = True
        self.calls.append(("shutdown",))

    def restart(self) -> None:
        self.restart_called = True
        self.calls.append(("restart",))

    def take_screenshot(self, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"fake-png")
        self.calls.append(("screenshot", destination))
        return destination
