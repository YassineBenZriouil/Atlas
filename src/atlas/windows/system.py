"""System-level controls abstraction (Atlas.md section 22), plus the Win32
implementation.

Confirmation policy for destructive actions (shutdown/restart/lock/logout)
lives in atlas.security.permissions and is enforced by the dispatcher before
it ever calls into this interface - implementations here perform no
confirmation logic of their own."""

from __future__ import annotations

import ctypes
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class SystemController(ABC):
    @abstractmethod
    def mute(self) -> None: ...

    @abstractmethod
    def unmute(self) -> None: ...

    @abstractmethod
    def set_volume(self, level: int) -> None: ...

    @abstractmethod
    def volume_up(self, step: int = 10) -> None: ...

    @abstractmethod
    def volume_down(self, step: int = 10) -> None: ...

    @abstractmethod
    def lock(self) -> None: ...

    @abstractmethod
    def sleep(self) -> None: ...

    @abstractmethod
    def shutdown(self) -> None: ...

    @abstractmethod
    def restart(self) -> None: ...

    @abstractmethod
    def take_screenshot(self, destination: Path) -> Path: ...


def _volume_interface() -> IAudioEndpointVolume:
    return AudioUtilities.GetSpeakers().EndpointVolume


class Win32SystemController(SystemController):
    """shutdown()/restart() call the fixed `shutdown.exe` command line - never
    a string built from voice input - via subprocess with shell=False."""

    def mute(self) -> None:
        _volume_interface().SetMute(1, None)

    def unmute(self) -> None:
        _volume_interface().SetMute(0, None)

    def set_volume(self, level: int) -> None:
        level = max(0, min(100, level))
        _volume_interface().SetMasterVolumeLevelScalar(level / 100, None)

    def volume_up(self, step: int = 10) -> None:
        volume = _volume_interface()
        current = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(min(1.0, current + step / 100), None)

    def volume_down(self, step: int = 10) -> None:
        volume = _volume_interface()
        current = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(max(0.0, current - step / 100), None)

    def lock(self) -> None:
        ctypes.windll.user32.LockWorkStation()

    def sleep(self) -> None:
        ctypes.windll.powrprof.SetSuspendState(False, True, False)

    def shutdown(self) -> None:
        subprocess.Popen(["shutdown.exe", "/s", "/t", "0"], shell=False)

    def restart(self) -> None:
        subprocess.Popen(["shutdown.exe", "/r", "/t", "0"], shell=False)

    def take_screenshot(self, destination: Path) -> Path:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("No screen available to capture")
        pixmap = screen.grabWindow(0)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not pixmap.save(str(destination), "PNG"):
            raise RuntimeError(f"Failed to save screenshot to {destination}")
        return destination
