"""System controls interface (Atlas.md section 22).

Confirmation for destructive actions (shutdown/restart/...) lives in
atlas.security.permissions and is enforced by the dispatcher before any
backend is called - implementations do no confirmation of their own."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


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
