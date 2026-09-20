"""Application discovery/lifecycle abstraction (Atlas.md section 18), plus
the Win32/filesystem-backed implementation. Maps spoken aliases (configured
in atlas.config) to executables."""

from __future__ import annotations

import difflib
import shutil
import winreg
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from atlas.config.schema import AtlasConfig
from atlas.utils.process import launch_executable
from atlas.windows.windows import WindowHandle, WindowManager

_FUZZY_ALIAS_CUTOFF = 0.75


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


class ApplicationNotFoundError(RuntimeError):
    pass


class Win32ApplicationManager(ApplicationManager):
    """Resolution order for `locate`: configured executable path -> PATH
    lookup -> the Windows "App Paths" registry. Never falls back to
    guessing/fuzzy-matching a *path* - an unresolved application is
    reported as not found (Atlas.md section 56), not silently
    substituted. `resolve_alias` does allow one deterministic fuzzy step
    (see `_resolve_alias_fuzzy`), but only across already-configured
    alias text - never onto an arbitrary path."""

    def __init__(self, config: AtlasConfig, window_manager: WindowManager) -> None:
        self._config = config
        self._window_manager = window_manager

    def resolve_alias(self, alias: str) -> ApplicationInfo | None:
        alias_lower = alias.lower().strip()
        for key, entry in self._config.applications.items():
            if alias_lower == key.lower() or alias_lower in (a.lower() for a in entry.aliases):
                return ApplicationInfo(alias=key, executable_path=entry.executable or None)
        return self._resolve_alias_fuzzy(alias_lower)

    def _resolve_alias_fuzzy(self, alias_lower: str) -> ApplicationInfo | None:
        """Deterministic fallback for ASR misrecognitions of an otherwise
        correctly *configured* alias (Atlas.md section 63: fuzzy matching
        is permitted for application names, but must never bypass safety
        validation - this only ever resolves to an alias already present
        in config, never invents a path, and command verbs/dangerous
        command names are matched by exact grammar elsewhere and are
        never reachable through this method at all)."""
        candidates: dict[str, str] = {}
        for key, entry in self._config.applications.items():
            candidates[key.lower()] = key
            for a in entry.aliases:
                candidates[a.lower()] = key

        match = difflib.get_close_matches(
            alias_lower, candidates.keys(), n=1, cutoff=_FUZZY_ALIAS_CUTOFF
        )
        if not match:
            return None
        key = candidates[match[0]]
        entry = self._config.applications[key]
        return ApplicationInfo(alias=key, executable_path=entry.executable or None)

    def locate(self, alias: str) -> str | None:
        info = self.resolve_alias(alias)
        candidates = [alias]
        if info is not None:
            if info.executable_path and Path(info.executable_path).exists():
                return info.executable_path
            entry = self._config.applications.get(info.alias)
            configured_aliases = entry.aliases if entry is not None else []
            # Multi-word aliases (e.g. "vs code") are never real command
            # names; single-word ones (e.g. "code") often are the actual
            # executable/shim name and are worth trying on PATH.
            candidates = [info.alias, alias, *(a for a in configured_aliases if " " not in a)]

        for name in candidates:
            found = shutil.which(name) or shutil.which(f"{name}.exe")
            if found:
                return found

        for name in candidates:
            found = self._locate_via_app_paths(name)
            if found:
                return found
        return None

    @staticmethod
    def _locate_via_app_paths(name: str) -> str | None:
        registry_key = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{name}.exe"
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive, registry_key) as key:
                    value, _ = winreg.QueryValueEx(key, "")
            except OSError:
                continue
            if value and Path(value).exists():
                return value
        return None

    def launch(self, alias: str) -> None:
        path = self.locate(alias)
        if path is None:
            raise ApplicationNotFoundError(f"'{alias}' was not found")
        launch_executable(path)

    def _process_names_for(self, alias: str) -> set[str]:
        names = {alias.lower()}
        info = self.resolve_alias(alias)
        if info is not None:
            names.add(info.alias.lower())
            if info.executable_path:
                names.add(Path(info.executable_path).name.lower())
        path = self.locate(alias)
        if path:
            names.add(Path(path).name.lower())
        return names

    def _title_fragments_for(self, alias: str) -> set[str]:
        """A launcher shim (e.g. VS Code's `code.CMD`) is a different
        process from the GUI window it starts, so process-name matching
        alone misses it. Configured multi-word aliases (e.g. "visual
        studio code") are checked against the window title as a
        deterministic fallback - still an exact substring match against
        admin-configured strings, not fuzzy/statistical matching."""
        fragments = {alias.lower()}
        info = self.resolve_alias(alias)
        if info is None:
            return fragments
        fragments.add(info.alias.lower())
        entry = self._config.applications.get(info.alias)
        if entry is not None:
            fragments.update(a.lower() for a in entry.aliases)
        return {f for f in fragments if len(f) > 2}

    def windows_for(self, alias: str) -> list[WindowHandle]:
        names = self._process_names_for(alias)
        title_fragments = self._title_fragments_for(alias)
        matches = []
        for window in self._window_manager.list_windows():
            if window.process_name.lower() in names:
                matches.append(window)
                continue
            title_lower = window.title.lower()
            if any(fragment in title_lower for fragment in title_fragments):
                matches.append(window)
        return matches

    def is_running(self, alias: str) -> bool:
        return len(self.windows_for(alias)) > 0

    def terminate(self, alias: str) -> None:
        for window in self.windows_for(alias):
            self._window_manager.close_window(window)
