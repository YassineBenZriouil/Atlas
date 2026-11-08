"""Installed-application discovery (Atlas.md section 18: "Where possible,
ATLAS should automatically locate applications rather than requiring
paths"). Two sources, combined:

- Classic Start Menu shortcuts (both per-user and all-users), resolved to
  their real target .exe via the shell's own COM shortcut resolver - the
  same mechanism Explorer itself uses, so it's exactly as accurate as
  "what shows up when you open the Start Menu".
- Store/UWP apps, which have no real file path to resolve - enumerated
  via the `Get-StartApps` PowerShell cmdlet (there is no simpler win32
  API for this) and launched through `shell:AppsFolder\\<AppID>` instead.

Never launches anything itself - this only produces a list of
(name, launch target) pairs for atlas.config to merge in, and it is the
same launch-target format Win32ApplicationManager already understands."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import win32com.client

from atlas.logging_setup import get_logger
from atlas.platform.discovery import DiscoveredApp

logger = get_logger("discovery")

_START_MENU_DIRS = (
    r"%APPDATA%\Microsoft\Windows\Start Menu\Programs",
    r"%ProgramData%\Microsoft\Windows\Start Menu\Programs",
)

_SKIP_NAME_SUBSTRINGS = (
    "uninstall",
    "readme",
    "release notes",
    "documentation",
    "faq",
    "help",
    "on the web",
    "support center",
    "manuals",
    "module docs",
    "license",
)

UWP_TARGET_PREFIX = "uwp:"


def _should_skip(name: str) -> bool:
    lowered = name.lower()
    return any(skip in lowered for skip in _SKIP_NAME_SUBSTRINGS)


def discover_shortcut_apps() -> list[DiscoveredApp]:
    shell = win32com.client.Dispatch("WScript.Shell")
    found: dict[str, DiscoveredApp] = {}

    for base in _START_MENU_DIRS:
        base_path = Path(os.path.expandvars(base))
        if not base_path.exists():
            continue
        for lnk in base_path.rglob("*.lnk"):
            name = lnk.stem
            if _should_skip(name):
                continue
            try:
                target = shell.CreateShortcut(str(lnk)).TargetPath
            except Exception:  # noqa: BLE001 - a single unreadable shortcut shouldn't abort discovery
                continue
            if not target or not target.lower().endswith(".exe"):
                continue
            if not Path(target).exists():
                continue
            found.setdefault(name.lower(), DiscoveredApp(name=name, target=target))

    return list(found.values())


def discover_uwp_apps() -> list[DiscoveredApp]:
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("Could not enumerate Store apps: %s", exc)
        return []

    try:
        raw = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(raw, dict):
        raw = [raw]

    apps: list[DiscoveredApp] = []
    for entry in raw:
        name = entry.get("Name", "")
        app_id = entry.get("AppID", "")
        if not name or "!" not in app_id or _should_skip(name):
            continue
        apps.append(DiscoveredApp(name=name, target=f"{UWP_TARGET_PREFIX}{app_id}"))
    return apps


def discover_installed_applications() -> list[DiscoveredApp]:
    return discover_shortcut_apps() + discover_uwp_apps()
