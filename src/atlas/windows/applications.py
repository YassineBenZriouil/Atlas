"""Application discovery/lifecycle abstraction (Atlas.md section 18). Maps
spoken aliases to executables; the real Win32/filesystem lookup logic is a
Phase 2 concern."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from atlas.windows.windows import WindowHandle


@dataclass(frozen=True)
class ApplicationInfo:
    alias: str
    executable_path: str | None


class ApplicationManager(ABC):
    @abstractmethod
    def resolve_alias(self, alias: str) -> ApplicationInfo | None: ...

    @abstractmethod
    def locate(self, alias: str) -> str | None: ...

    @abstractmethod
    def launch(self, alias: str) -> None: ...

    @abstractmethod
    def terminate(self, alias: str) -> None: ...

    @abstractmethod
    def is_running(self, alias: str) -> bool: ...

    @abstractmethod
    def windows_for(self, alias: str) -> list[WindowHandle]: ...
