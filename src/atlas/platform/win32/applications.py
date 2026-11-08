"""Win32/filesystem-backed ApplicationManager (Atlas.md section 18)."""

from __future__ import annotations

import shutil
import subprocess
import winreg
from pathlib import Path

from atlas.config.schema import AtlasConfig
from atlas.platform.applications import (
    ApplicationInfo,
    ApplicationManager,
    ApplicationNotFoundError,
    resolve_configured_alias,
)
from atlas.platform.win32.discovery import UWP_TARGET_PREFIX
from atlas.platform.windowing import WindowHandle, WindowManager
from atlas.utils.process import launch_executable


def _runs_from_package(process_path: str, name: str, publisher: str) -> bool:
    """Store apps run from .../WindowsApps/<Name>_<version>_<arch>__<Publisher>/,
    whatever their window title says (e.g. Windows Terminal shows the shell's)."""
    folder = Path(process_path).parent.name.lower()
    return folder.startswith(f"{name.lower()}_") and folder.endswith(f"__{publisher.lower()}")


class Win32ApplicationManager(ApplicationManager):
    """Resolution order for `locate`: configured executable path -> PATH
    lookup -> the Windows "App Paths" registry. Never falls back to
    guessing/fuzzy-matching a *path* - an unresolved application is
    reported as not found (Atlas.md section 56), not silently
    substituted. `resolve_alias` does allow one deterministic fuzzy step
    (see `atlas.platform.applications`), but only across already-configured
    alias text - never onto an arbitrary path."""

    def __init__(self, config: AtlasConfig, window_manager: WindowManager) -> None:
        self._config = config
        self._window_manager = window_manager
        # app key -> its window handles that existed when ATLAS last launched it
        self._before_launch: dict[str, set[int]] = {}

    def _key(self, alias: str) -> str:
        info = self.resolve_alias(alias)
        return info.alias if info is not None else alias.lower().strip()

    def resolve_alias(self, alias: str) -> ApplicationInfo | None:
        return resolve_configured_alias(self._config, alias)

    def locate(self, alias: str) -> str | None:
        info = self.resolve_alias(alias)
        candidates = [alias]
        if info is not None:
            if info.executable_path and info.executable_path.startswith(UWP_TARGET_PREFIX):
                return info.executable_path
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
        self._before_launch[self._key(alias)] = {w.handle for w in self.windows_for(alias)}
        if path.startswith(UWP_TARGET_PREFIX):
            app_id = path[len(UWP_TARGET_PREFIX) :]
            # Store apps have no real .exe to launch directly; this is the
            # standard way to start one from outside the Start Menu itself.
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"], shell=False)
            return
        launch_executable(path)

    def _process_names_for(self, alias: str) -> set[str]:
        names = {alias.lower()}
        info = self.resolve_alias(alias)
        if info is not None:
            names.add(info.alias.lower())
            if info.executable_path and not info.executable_path.startswith(UWP_TARGET_PREFIX):
                names.add(Path(info.executable_path).name.lower())
        path = self.locate(alias)
        if path and not path.startswith(UWP_TARGET_PREFIX):
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
        """Every command acts on [0] when an app has several windows: the one
        ATLAS opened most recently if it's still open, otherwise the app's
        most recently used window (Windows lists windows front to back)."""
        names = self._process_names_for(alias)
        title_fragments = self._title_fragments_for(alias)
        package = self._uwp_package_for(alias)
        matches = []
        for window in self._window_manager.list_windows():
            if window.process_name.lower() in names or (
                package and _runs_from_package(window.process_path, *package)
            ):
                matches.append(window)
                continue
            title_lower = window.title.lower()
            if any(fragment in title_lower for fragment in title_fragments):
                matches.append(window)
        existing = self._before_launch.get(self._key(alias))
        if existing is not None:
            matches.sort(key=lambda window: window.handle in existing)  # stable: new ones first
        return matches

    def _uwp_package_for(self, alias: str) -> tuple[str, str] | None:
        """(package name, publisher id) from a "uwp:Name_Publisher!App" target."""
        info = self.resolve_alias(alias)
        target = info.executable_path if info is not None else None
        if not target or not target.startswith(UWP_TARGET_PREFIX):
            return None
        family = target[len(UWP_TARGET_PREFIX) :].split("!", 1)[0]
        name, _, publisher = family.rpartition("_")
        return (name, publisher) if name and publisher else None

    def is_running(self, alias: str) -> bool:
        return len(self.windows_for(alias)) > 0

    def terminate(self, alias: str) -> None:
        """Closes one window (the same one other commands would act on), not
        every window of the app - "close terminal" must not take down the
        terminal you're working in."""
        windows = self.windows_for(alias)
        if windows:
            self._window_manager.close_window(windows[0])
