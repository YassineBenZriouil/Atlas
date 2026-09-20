"""Safe process helpers. Never pass raw user/voice input to a shell."""

from __future__ import annotations

import subprocess
from pathlib import Path


class ProcessLaunchError(RuntimeError):
    pass


def launch_executable(executable: Path | str, args: list[str] | None = None) -> subprocess.Popen:
    """Launch a known, validated executable path. `shell` is never enabled.

    Callers MUST resolve `executable` against a trusted registry (e.g. the
    application manager's configured/discovered paths) - never pass raw
    speech transcript text here.
    """
    path = Path(executable)
    if not path.exists():
        raise ProcessLaunchError(f"Executable not found: {path}")
    try:
        return subprocess.Popen([str(path), *(args or [])], shell=False)
    except OSError as exc:
        raise ProcessLaunchError(f"Failed to launch {path}: {exc}") from exc


