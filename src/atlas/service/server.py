"""Local HTTP API for the core (stdlib only). Binds 127.0.0.1, and every
request must carry the bearer token from the discovery file - browsers
can't send that header cross-origin without a CORS preflight we never
answer, so web pages can't drive ATLAS."""

from __future__ import annotations

import hmac
import json
import os
import queue
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs

from atlas.config.loader import ConfigError
from atlas.logging_setup import get_logger
from atlas.platform import PlatformNotSupportedError
from atlas.service.client import CoreInfo, connect, remove_discovery, write_discovery
from atlas.service.core import AtlasCore

logger = get_logger("server")

_KEEPALIVE_SECONDS = 15.0
_MAX_BODY_BYTES = 1_000_000


class _ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class CoreServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, core: AtlasCore, port: int = 0, token: str | None = None) -> None:
        super().__init__(("127.0.0.1", port), _Handler)
        self.core = core
        self.token = token or secrets.token_urlsafe(32)

    @property
    def port(self) -> int:
        return int(self.server_address[1])

    def request_quit(self) -> None:
        # shutdown() blocks until serve_forever returns, so never on the serving thread.
        threading.Thread(target=self.shutdown, daemon=True).start()


class _Handler(BaseHTTPRequestHandler):
    server: CoreServer

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        logger.debug("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:  # noqa: N802
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._handle("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._handle("PUT")

    def _handle(self, method: str) -> None:
        if not hmac.compare_digest(
            self.headers.get("Authorization", ""), f"Bearer {self.server.token}"
        ):
            self._send(401, {"error": "unauthorized"})
            return
        path, _, query = self.path.partition("?")
        if (method, path) == ("GET", "/api/events"):
            self._stream_events()
            return
        try:
            body = self._read_json() if method in ("POST", "PUT") else {}
            status, payload = self._route(method, path, body, parse_qs(query))
        except _ApiError as exc:
            status, payload = exc.status, {"error": str(exc)}
        except PlatformNotSupportedError as exc:
            status, payload = 501, {"error": str(exc)}
        self._send(status, payload)

    def _route(
        self, method: str, path: str, body: dict[str, Any], query: dict[str, list[str]]
    ) -> tuple[int, Any]:
        core = self.server.core
        match (method, path):
            case ("GET", "/api/status"):
                return 200, core.status()
            case ("GET", "/api/history"):
                return 200, core.events.history()
            case ("POST", "/api/command"):
                text = body.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise _ApiError(400, "'text' must be a non-empty string")
                return 200, core.run_command(text.strip())
            case ("POST", "/api/voice"):
                enabled = body.get("enabled")
                if not isinstance(enabled, bool):
                    raise _ApiError(400, "'enabled' must be true or false")
                core.set_voice(enabled)
                return 200, core.status()["voice"]
            case ("GET", "/api/config"):
                return 200, core.config()
            case ("PUT", "/api/config"):
                try:
                    core.update_config(body)
                except ConfigError as exc:
                    raise _ApiError(400, f"Invalid configuration: {exc}") from exc
                return 200, core.config()
            case ("POST", "/api/reload"):
                core.reload()
                return 200, {"ok": True}
            case ("GET", "/api/plugins"):
                return 200, core.plugins()
            case ("GET", "/api/logs"):
                try:
                    lines = int(query.get("lines", ["200"])[0])
                except ValueError as exc:
                    raise _ApiError(400, "'lines' must be an integer") from exc
                return 200, core.logs(lines)
            case ("POST", "/api/apps/discover"):
                return 200, core.discover_apps()
            case ("POST", "/api/quit"):
                self.server.request_quit()
                return 200, {"ok": True}
        raise _ApiError(404, f"no route for {method} {path}")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length > _MAX_BODY_BYTES:
            raise _ApiError(413, "request body too large")
        if length == 0:
            return {}
        try:
            body = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _ApiError(400, "body must be JSON") from exc
        if not isinstance(body, dict):
            raise _ApiError(400, "body must be a JSON object")
        return body

    def _send(self, status: int, payload: Any) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _stream_events(self) -> None:
        """Server-Sent Events: one `data: {json}` per event; comment lines
        as keepalive so a vanished client is noticed within ~15 s."""
        subscriber = self.server.core.events.subscribe()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    event = subscriber.get(timeout=_KEEPALIVE_SECONDS)
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue
                if event is None:
                    break
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                self.wfile.flush()
        except OSError:
            pass  # client went away
        finally:
            self.server.core.events.unsubscribe(subscriber)


def run_core(*, voice: bool = True) -> int:
    """Foreground entry point (`atlas core`). Single instance per user:
    exits if a live core already answers on the discovery file."""
    if connect() is not None:
        print("ATLAS core is already running.")
        return 1

    core = AtlasCore()
    core.start(voice=voice)
    server = CoreServer(core)
    info = CoreInfo(port=server.port, token=server.token, pid=os.getpid())
    write_discovery(info)
    logger.info("ATLAS core listening on 127.0.0.1:%d", server.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        core.shutdown()
        server.server_close()
        remove_discovery(info)
    return 0
