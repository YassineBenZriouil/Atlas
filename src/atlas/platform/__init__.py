"""The OS layer (docs/ROADMAP.md, Phase 4). Everything above this package
(commands, parser, core, window) uses only the interfaces defined here;
`get_backend()` supplies this OS's implementations.

Windows (`atlas.platform.win32`) is the only full backend. Anywhere else
ATLAS still starts - config, the core, the window, typed commands and
Vosk voice all work - and each OS action fails with a clear
PlatformNotSupportedError instead of an import crash. Adding macOS or
Linux means writing `atlas/platform/<os>/` with a `create_backend()` and
registering it in `_BACKEND_MODULES`; nothing else changes."""

from __future__ import annotations

import functools
import importlib
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from atlas.config.schema import AtlasConfig
from atlas.platform.applications import ApplicationManager
from atlas.platform.discovery import DiscoveredApp
from atlas.platform.keyboard import KeyboardController
from atlas.platform.monitors import MonitorManager
from atlas.platform.mouse import MouseController
from atlas.platform.secrets import SecretStore
from atlas.platform.system import SystemController
from atlas.platform.windowing import WindowManager

_BACKEND_MODULES = {"win32": "atlas.platform.win32"}


class PlatformNotSupportedError(RuntimeError):
    def __init__(self, feature: str, platform: str = sys.platform) -> None:
        super().__init__(f"{feature} isn't supported on {platform} yet")
        self.feature = feature


@dataclass(frozen=True)
class PlatformBackend:
    name: str
    window_manager: Callable[[], WindowManager]
    monitor_manager: Callable[[], MonitorManager]
    keyboard_controller: Callable[[], KeyboardController]
    mouse_controller: Callable[[], MouseController]
    system_controller: Callable[[], SystemController]
    application_manager: Callable[[AtlasConfig, WindowManager], ApplicationManager]
    secret_store: SecretStore
    discover_applications: Callable[[], list[DiscoveredApp]]
    # `[speech] engine` name -> voice loop factory(app, on_event) for OS recognizers.
    voice_engines: dict[str, Callable[..., Any]] = field(default_factory=dict)
    # Factory for the "native" transcriber of the Vosk engine's provider chain.
    native_transcriber: Callable[[], Any] | None = None
    # Why the OS speech engine can't work right now ("" when it's ready).
    speech_problem: Callable[[], str] | None = None


def unsupported(interface: Any, feature: str) -> Any:
    """A concrete `interface` whose every method raises
    PlatformNotSupportedError - lets ATLAS run where a backend is missing."""

    def fail(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise PlatformNotSupportedError(feature)

    methods = {name: fail for name in getattr(interface, "__abstractmethods__", ())}
    return type(f"Unsupported{interface.__name__}", (interface,), methods)


def _fallback_backend() -> PlatformBackend:
    unsupported_apps = unsupported(ApplicationManager, "Application control")

    def no_discovery() -> list[DiscoveredApp]:
        raise PlatformNotSupportedError("Application discovery")

    return PlatformBackend(
        name=sys.platform,
        window_manager=unsupported(WindowManager, "Window control"),
        monitor_manager=unsupported(MonitorManager, "Monitor detection"),
        keyboard_controller=unsupported(KeyboardController, "Keyboard control"),
        mouse_controller=unsupported(MouseController, "Mouse control"),
        system_controller=unsupported(SystemController, "System control"),
        application_manager=lambda config, windows: unsupported_apps(),
        secret_store=unsupported(SecretStore, "Secure credential storage")(),
        discover_applications=no_discovery,
    )


@functools.cache
def get_backend() -> PlatformBackend:
    module_name = _BACKEND_MODULES.get(sys.platform)
    if module_name is None:
        return _fallback_backend()
    backend: PlatformBackend = importlib.import_module(module_name).create_backend()
    return backend


def open_path(target: str) -> None:
    """Open a folder, file or URI with the OS default handler. `target` must
    come from ATLAS itself (a resolved folder, a settings URI) - never raw
    voice text."""
    if sys.platform == "win32":
        import os

        os.startfile(target)  # type: ignore[attr-defined]  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])
