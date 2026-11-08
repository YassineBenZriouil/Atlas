"""Moves core-API work off the Qt thread. Every API call and the event
stream run on plain Python threads and report back through Qt signals,
which Qt queues onto the UI thread - widgets are never touched from a
worker thread, and a slow command never freezes the window."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal

from atlas.service.client import CoreApiError, CoreClient, CoreUnavailableError

ClientProvider = Callable[[], CoreClient | None]


class CoreBridge(QObject):
    core_event = Signal(dict)
    connected = Signal(object)  # CoreClient, or None when the core is gone
    _done = Signal(object, object, object)  # on_ok, on_error, result-or-exception

    def __init__(self, client_provider: ClientProvider, retry_seconds: float = 2.0) -> None:
        super().__init__()
        self._provider = client_provider
        self._retry_seconds = retry_seconds
        self._stopped = threading.Event()
        self.client: CoreClient | None = None
        self._done.connect(self._deliver)
        self.connected.connect(self._set_client)

    def start(self) -> None:
        threading.Thread(target=self._pump, name="atlas-events", daemon=True).start()

    def stop(self) -> None:
        self._stopped.set()

    def _set_client(self, client: CoreClient | None) -> None:
        self.client = client

    def _pump(self) -> None:
        """Connect, stream events until the core goes away, repeat. A core
        restarted elsewhere gets a new port/token, so reconnects re-read
        discovery through the provider every time."""
        while not self._stopped.is_set():
            client = self._provider()
            if client is None:
                self.connected.emit(None)
                self._stopped.wait(self._retry_seconds)
                continue
            self.connected.emit(client)
            try:
                for event in client.events():
                    if self._stopped.is_set():
                        return
                    self.core_event.emit(event)
            except (CoreUnavailableError, CoreApiError):
                pass
            self.connected.emit(None)
            self._stopped.wait(self._retry_seconds / 2)

    def call(
        self,
        fn: Callable[[CoreClient], Any],
        on_ok: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Run `fn(client)` on a worker thread; callbacks run on the UI thread."""
        client = self.client
        if client is None:
            if on_error is not None:
                on_error(CoreUnavailableError("Not connected to the ATLAS core"))
            return

        def work() -> None:
            try:
                result: Any = fn(client)
            except (CoreUnavailableError, CoreApiError) as exc:
                result = exc
            self._done.emit(on_ok, on_error, result)

        threading.Thread(target=work, daemon=True).start()

    def run_in_thread(
        self,
        fn: Callable[[], Any],
        on_ok: Callable[[Any], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """For work that doesn't need a connected client (starting the core)."""

        def work() -> None:
            try:
                result: Any = fn()
            except (CoreUnavailableError, CoreApiError) as exc:
                result = exc
            self._done.emit(on_ok, on_error, result)

        threading.Thread(target=work, daemon=True).start()

    def _deliver(self, on_ok: Any, on_error: Any, result: Any) -> None:
        if isinstance(result, Exception):
            if on_error is not None:
                on_error(result)
        elif on_ok is not None:
            on_ok(result)
