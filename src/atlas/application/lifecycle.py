"""Startup/shutdown sequencing and crash-loop protection (Atlas.md section 66)."""

from __future__ import annotations

import time
from collections.abc import Callable

from atlas.logging_setup import get_logger

logger = get_logger("lifecycle")

Hook = Callable[[], None]


class CrashGuard:
    """Tracks recent crashes so Application can refuse to enter a restart loop."""

    def __init__(self, max_restarts: int = 3, cooldown_seconds: float = 30.0) -> None:
        self.max_restarts = max_restarts
        self.cooldown_seconds = cooldown_seconds
        self._crash_times: list[float] = []

    def record_crash(self) -> None:
        now = time.monotonic()
        self._crash_times.append(now)
        cutoff = now - self.cooldown_seconds
        self._crash_times = [t for t in self._crash_times if t >= cutoff]

    def should_restart(self) -> bool:
        return len(self._crash_times) < self.max_restarts

    def reset(self) -> None:
        self._crash_times.clear()


class Lifecycle:
    """Startup hooks may raise (the caller decides fail-fast vs. recovery).
    Shutdown hooks are always best-effort so a broken hook never blocks a
    clean exit."""

    def __init__(self) -> None:
        self._startup_hooks: list[tuple[str, Hook]] = []
        self._shutdown_hooks: list[tuple[str, Hook]] = []

    def on_startup(self, name: str, hook: Hook) -> None:
        self._startup_hooks.append((name, hook))

    def on_shutdown(self, name: str, hook: Hook) -> None:
        self._shutdown_hooks.append((name, hook))

    def startup(self) -> None:
        for name, hook in self._startup_hooks:
            logger.info("Startup: %s", name)
            hook()

    def shutdown(self) -> None:
        for name, hook in reversed(self._shutdown_hooks):
            try:
                logger.info("Shutdown: %s", name)
                hook()
            except Exception:  # noqa: BLE001 - shutdown must never abort partway
                logger.exception("Shutdown hook '%s' failed", name)
