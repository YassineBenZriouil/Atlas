"""Finding, starting and talking to the core service. Used by the CLI and
(Phase 3) the window."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from atlas.utils.paths import get_app_data_dir

_DISCOVERY_FILE = "core.json"


class CoreUnavailableError(RuntimeError):
    pass


class CoreApiError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


@dataclass(frozen=True)
class CoreInfo:
    port: int
    token: str
    pid: int


def discovery_path() -> Path:
    return get_app_data_dir() / _DISCOVERY_FILE


def write_discovery(info: CoreInfo) -> None:
    discovery_path().write_text(json.dumps(asdict(info)), encoding="utf-8")


def read_discovery() -> CoreInfo | None:
    try:
        data = json.loads(discovery_path().read_text(encoding="utf-8"))
        return CoreInfo(port=int(data["port"]), token=str(data["token"]), pid=int(data["pid"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def remove_discovery(info: CoreInfo) -> None:
    """Only removes the file if it still describes this core."""
    if read_discovery() == info:
        discovery_path().unlink(missing_ok=True)


class CoreClient:
    def __init__(self, info: CoreInfo, timeout: float = 10.0) -> None:
        self.info = info
        self._base = f"http://127.0.0.1:{info.port}"
        self._headers = {"Authorization": f"Bearer {info.token}"}
        self._timeout = timeout

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        try:
            response = requests.request(
                method,
                self._base + path,
                headers=self._headers,
                json=body,
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise CoreUnavailableError(f"ATLAS core not reachable: {exc}") from exc
        try:
            payload = response.json()
        except ValueError:
            payload = {"error": response.text}
        if response.status_code != 200:
            raise CoreApiError(response.status_code, payload.get("error", ""))
        return payload

    def status(self) -> dict[str, Any]:
        return self.request("GET", "/api/status")

    def history(self) -> list[dict[str, Any]]:
        return self.request("GET", "/api/history")

    def run_command(self, text: str) -> dict[str, Any]:
        return self.request("POST", "/api/command", {"text": text})

    def set_voice(self, enabled: bool) -> dict[str, Any]:
        return self.request("POST", "/api/voice", {"enabled": enabled})

    def config(self) -> dict[str, Any]:
        return self.request("GET", "/api/config")

    def update_config(self, config: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", "/api/config", config)

    def reload(self) -> None:
        self.request("POST", "/api/reload")

    def plugins(self) -> list[dict[str, str]]:
        return self.request("GET", "/api/plugins")

    def logs(self, lines: int = 200) -> list[str]:
        return self.request("GET", f"/api/logs?lines={lines}")

    def discover_apps(self) -> dict[str, list[str]]:
        return self.request("POST", "/api/apps/discover")

    def quit(self) -> None:
        self.request("POST", "/api/quit")

    def events(self) -> Iterator[dict[str, Any]]:
        """Blocks, yielding events as the core publishes them. Ends when the
        core shuts down; raises CoreUnavailableError if it can't connect."""
        try:
            response = requests.get(
                self._base + "/api/events",
                headers=self._headers,
                stream=True,
                timeout=(self._timeout, None),
            )
        except requests.RequestException as exc:
            raise CoreUnavailableError(f"ATLAS core not reachable: {exc}") from exc
        with response:
            if response.status_code != 200:
                raise CoreApiError(response.status_code, "event stream refused")
            try:
                # chunk_size=1: the default (512) holds small events back until more arrive.
                for line in response.iter_lines(chunk_size=1):
                    if line.startswith(b"data: "):
                        yield json.loads(line[len(b"data: ") :])
            except requests.RequestException:
                return


def connect() -> CoreClient | None:
    """A client for the running core, or None if none answers."""
    info = read_discovery()
    if info is None:
        return None
    client = CoreClient(info, timeout=2.0)
    try:
        client.status()
    except (CoreUnavailableError, CoreApiError):
        return None
    return CoreClient(info)


def start_core_detached() -> None:
    """Launches `atlas core` as an independent background process that
    outlives this one (and the terminal that started it)."""
    command = [sys.executable, "-m", "atlas", "core"]
    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            # Escape the launcher's job object (e.g. `uv run`) so the core isn't
            # killed when the launcher exits.
            subprocess.Popen(
                command, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kwargs
            )
            return
        except OSError:
            pass  # job forbids breakaway; fall back to a plain detached child
        subprocess.Popen(command, creationflags=flags, **kwargs)
    else:
        subprocess.Popen(command, start_new_session=True, **kwargs)


def ensure_core(timeout_seconds: float = 30.0) -> CoreClient:
    client = connect()
    if client is not None:
        return client
    start_core_detached()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        time.sleep(0.25)
        client = connect()
        if client is not None:
            return client
    raise CoreUnavailableError(
        f"ATLAS core did not start within {timeout_seconds:.0f}s - see the log file"
    )
