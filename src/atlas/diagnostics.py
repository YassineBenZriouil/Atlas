"""`atlas --diagnose` (Atlas.md section 37). Exercises everything that
exists today for real; only Spotify authentication remains unimplemented."""

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

    results.append(_check_windows_api())
    results.append(_check_monitor_detection())
    results.append(_check_application_discovery(app))
    results.append(_check_microphone())
    results.append(_check_speech_model(app))
    results.append(_check_wake_detector(app))
    results.append(_check_tts())
    results.append(
        CheckResult("Spotify authentication", CheckStatus.WARN, "Not yet implemented")
    )

    return results


def _check_windows_api() -> CheckResult:
    try:
        from atlas.windows.windows import Win32WindowManager

        count = len(Win32WindowManager().list_windows())
        return CheckResult("Windows API", CheckStatus.PASS, f"{count} visible window(s)")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Windows API", CheckStatus.FAIL, str(exc))


def _check_monitor_detection() -> CheckResult:
    try:
        from atlas.windows.monitors import Win32MonitorManager

        monitors = Win32MonitorManager().list_monitors()
        return CheckResult("Monitor detection", CheckStatus.PASS, f"{len(monitors)} monitor(s)")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Monitor detection", CheckStatus.FAIL, str(exc))


def _check_application_discovery(app: Application) -> CheckResult:
    try:
        assert app.application_manager is not None
        found = [
            alias
            for alias in app.config.applications  # type: ignore[union-attr]
            if app.application_manager.locate(alias)
        ]
        return CheckResult(
            "Application discovery", CheckStatus.PASS, f"resolved {len(found)} configured alias(es)"
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Application discovery", CheckStatus.FAIL, str(exc))


def _check_microphone() -> CheckResult:
    try:
        from atlas.audio.microphone import SoundDeviceMicrophone

        devices = SoundDeviceMicrophone().list_devices()
        if not devices:
            return CheckResult("Microphone", CheckStatus.WARN, "No input devices found")
        return CheckResult("Microphone", CheckStatus.PASS, f"{len(devices)} input device(s)")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Microphone", CheckStatus.FAIL, str(exc))


def _check_speech_model(app: Application) -> CheckResult:
    from atlas.speech.vosk_engine import SpeechEngineError, VoskSpeechEngine, find_default_model

    model_path = find_default_model(app.config.speech.model_path if app.config else "")
    if model_path is None:
        return CheckResult(
            "Speech engine / model", CheckStatus.WARN, "No Vosk model found - see models/README.md"
        )
    try:
        engine = VoskSpeechEngine(model_path)
        engine.start()
        return CheckResult("Speech engine / model", CheckStatus.PASS, str(model_path))
    except SpeechEngineError as exc:
        return CheckResult("Speech engine / model", CheckStatus.FAIL, str(exc))


def _check_wake_detector(app: Application) -> CheckResult:
    from atlas.speech.vosk_engine import find_default_model
    from atlas.wake.detector import VoskWakeDetector

    assert app.config is not None
    model_path = find_default_model(app.config.speech.model_path)
    if model_path is None:
        return CheckResult("Wake detector", CheckStatus.WARN, "No Vosk model found")
    try:
        detector = VoskWakeDetector(model_path, wake_phrase=app.config.wake.phrase)
        detector.start()
        return CheckResult("Wake detector", CheckStatus.PASS, f"phrase: '{app.config.wake.phrase}'")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Wake detector", CheckStatus.FAIL, str(exc))


def _check_tts() -> CheckResult:
    try:
        from atlas.speech.tts import Pyttsx3TTSProvider

        Pyttsx3TTSProvider()
        return CheckResult("TTS", CheckStatus.PASS, "pyttsx3 engine initialized")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("TTS", CheckStatus.WARN, str(exc))


def format_results(results: list[CheckResult]) -> str:
    lines = []
    for r in results:
        line = f"[{r.status.name}] {r.name}"
        if r.detail:
            line += f" - {r.detail}"
        lines.append(line)
    return "\n".join(lines)
