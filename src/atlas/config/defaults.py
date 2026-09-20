"""Default application aliases and folders shipped with a fresh install."""

from __future__ import annotations

from atlas.config.schema import ApplicationEntry, AtlasConfig


def default_config() -> AtlasConfig:
    config = AtlasConfig()
    config.applications = {
        "brave": ApplicationEntry(executable="", aliases=["brave", "brave browser"]),
        "vscode": ApplicationEntry(
            executable="", aliases=["vs code", "visual studio code", "code"]
        ),
        "spotify": ApplicationEntry(executable="", aliases=["spotify"]),
    }
    config.folders = {}
    return config
