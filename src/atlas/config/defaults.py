"""Default application aliases and folders shipped with a fresh install.

Executables are left empty for anything not guaranteed to be on PATH -
`atlas --discover-apps` (atlas.windows.discovery) fills in the real path
for whatever's actually installed on this machine without disturbing
these hand-picked alias lists."""

from __future__ import annotations

from atlas.config.schema import ApplicationEntry, AtlasConfig


def default_config() -> AtlasConfig:
    config = AtlasConfig()
    config.applications = {
        "brave": ApplicationEntry(executable="", aliases=["brave", "brave browser"]),
        "vscode": ApplicationEntry(
            executable="", aliases=["vs code", "visual studio code", "code"]
        ),
        "spotify": ApplicationEntry(executable="", aliases=["spotify", "spot", "spotty"]),
        "discord": ApplicationEntry(executable="", aliases=["discord", "disc", "discor"]),
        "settings": ApplicationEntry(executable="", aliases=["settings", "setting", "set"]),
        "notepad": ApplicationEntry(executable="", aliases=["notepad", "notes", "note"]),
        "terminal": ApplicationEntry(executable="", aliases=["terminal", "term"]),
        "explorer": ApplicationEntry(
            executable="", aliases=["file explorer", "explorer", "files"]
        ),
        "steam": ApplicationEntry(executable="", aliases=["steam"]),
    }
    config.folders = {}
    return config
