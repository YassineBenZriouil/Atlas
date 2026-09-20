"""`atlas --diagnose` (Atlas.md section 37). Exercises everything that exists
today; Phase-2 subsystems are reported as not-yet-implemented rather than
silently skipped."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum, auto

from atlas.application.app import Application


class CheckStatus(Enum):
    PASS = auto()
    WARN = auto()
    FAIL = auto()


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    detail: str = ""


_PHASE_2_SUBSYSTEMS = (
    "Microphone",
    "Speech engine / model",
    "Wake detector",
    "Windows API",
    "Monitor detection",
    "Application discovery",
    "TTS",
    "Spotify authentication",
)


def run_diagnostics() -> list[CheckResult]:
    results: list[CheckResult] = [
        CheckResult(
            "Python",
            CheckStatus.PASS if sys.version_info >= (3, 12) else CheckStatus.FAIL,
            sys.version.split()[0],
        )
    ]

    app = Application()
    try:
        app.bootstrap()
    except Exception as exc:  # noqa: BLE001 - diagnostics must never crash
        results.append(CheckResult("Configuration / logging", CheckStatus.FAIL, str(exc)))
        return results

    results.append(CheckResult("Configuration", CheckStatus.PASS))
    results.append(CheckResult("Logging", CheckStatus.PASS))
    plugin_count = len(app.plugin_registry.all())
    results.append(
        CheckResult("Plugin loader", CheckStatus.PASS, f"{plugin_count} plugin(s) discovered")
    )

    try:
        result = app.run_text_command("atlas test")
        status = CheckStatus.PASS if result.success else CheckStatus.FAIL
        results.append(CheckResult("Command pipeline", status, result.message))
    except Exception as exc:  # noqa: BLE001 - diagnostics must never crash
        results.append(CheckResult("Command pipeline", CheckStatus.FAIL, str(exc)))

    for name in _PHASE_2_SUBSYSTEMS:
        results.append(CheckResult(name, CheckStatus.WARN, "Implemented in Phase 2"))

    return results


def format_results(results: list[CheckResult]) -> str:
    lines = []
    for r in results:
        line = f"[{r.status.name}] {r.name}"
        if r.detail:
            line += f" - {r.detail}"
        lines.append(line)
    return "\n".join(lines)
