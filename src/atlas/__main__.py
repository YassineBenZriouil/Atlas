"""Development CLI (Atlas.md section 70)."""

from __future__ import annotations

import argparse
import sys
import time

from atlas import __version__
from atlas.application.app import Application
from atlas.diagnostics import format_results, run_diagnostics
from atlas.logging_setup import get_logger

logger = get_logger("cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas", description="ATLAS voice assistant")
    parser.add_argument("--version", action="store_true", help="Print the version and exit")
    parser.add_argument("--diagnose", action="store_true", help="Run diagnostics and exit")
    parser.add_argument("--test-microphone", action="store_true")
    parser.add_argument("--test-speech", action="store_true")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--list-monitors", action="store_true")
    parser.add_argument("--list-windows", action="store_true")
    parser.add_argument("--list-plugins", action="store_true")
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--tray", action="store_true", help="Start the tray application")
    return parser


def _list_devices() -> int:
    from atlas.audio.microphone import SoundDeviceMicrophone

    devices = SoundDeviceMicrophone().list_devices()
    if not devices:
        print("No input devices found.")
        return 0
    for device in devices:
        print(
            f"[{device.device_id}] {device.name} "
            f"(channels={device.max_input_channels}, rate={device.default_sample_rate})"
        )
    return 0


def _list_monitors() -> int:
    from atlas.windows.monitors import Win32MonitorManager

    for monitor in Win32MonitorManager().list_monitors():
        primary = " (primary)" if monitor.is_primary else ""
        print(f"#{monitor.index} {monitor.name}{primary} bounds={monitor.bounds}")
    return 0


def _list_windows() -> int:
    from atlas.windows.windows import Win32WindowManager

    for window in Win32WindowManager().list_windows():
        print(f"{window.process_name}: {window.title}")
    return 0


def _test_microphone() -> int:
    from atlas.audio.audio_stream import SoundDeviceAudioStream
    from atlas.audio.microphone import SoundDeviceMicrophone

    mic = SoundDeviceMicrophone(sample_rate=16000, channels=1)
    mic.open("default")
    stream = SoundDeviceAudioStream(mic, blocksize=8000)

    frames: list[bytes] = []
    print("Recording 2 seconds from the default microphone...")
    try:
        stream.start(frames.append)
        time.sleep(2.0)
    finally:
        stream.stop()

    total_bytes = sum(len(frame) for frame in frames)
    if total_bytes == 0:
        print("No audio captured - check microphone permissions/selection.")
        return 1
    print(f"Captured {len(frames)} frame(s), {total_bytes} bytes. Microphone OK.")
    return 0


def _test_speech() -> int:
    from atlas.speech.vosk_engine import SpeechEngineError, VoskSpeechEngine, find_default_model

    app = Application()
    app.bootstrap()
    assert app.config is not None
    model_path = find_default_model(app.config.speech.model_path)
    if model_path is None:
        print("No Vosk model found. See models/README.md.")
        return 1

    try:
        engine = VoskSpeechEngine(model_path)
        engine.start()
    except SpeechEngineError as exc:
        print(f"Failed to start speech engine: {exc}")
        return 1
    print(f"Speech engine loaded model at {model_path}.")
    return 0


def _run_tray(app: Application) -> int:
    """Wires the tray's callback-based interface (Atlas.md section 34) to a
    real Application - kept out of atlas.ui.tray itself so that module
    stays free of business logic, per its own docstring."""
    from atlas.ui.tray import TrayApplication

    assert app.config is not None
    state: dict[str, object] = {}

    def enable_voice() -> None:
        if "loop" in state:
            logger.info("Voice already enabled")
            return
        from atlas.application.voice_loop import VoiceLoop
        from atlas.speech.vosk_engine import find_default_model

        assert app.config is not None
        model_path = find_default_model(app.config.speech.model_path)
        if model_path is None:
            logger.warning("Cannot enable voice: no Vosk model found (see models/README.md)")
            return

        loop = VoiceLoop(
            app,
            model_path=str(model_path),
            device_id=app.config.audio.device,
            sample_rate=app.config.audio.sample_rate,
            wake_phrase=app.config.wake.phrase,
            listen_timeout_seconds=app.config.wake.timeout_seconds,
            # Audio callbacks run on a background thread - never touch Qt
            # widgets from here, just log.
            on_event=lambda kind, message: logger.info("voice: %s - %s", kind, message),
        )
        loop.start()
        state["loop"] = loop
        logger.info("Voice enabled")

    def disable_voice() -> None:
        loop = state.pop("loop", None)
        if loop is not None:
            loop.stop()  # type: ignore[attr-defined]
        logger.info("Voice disabled")

    def open_settings() -> None:
        from atlas.ui.settings import SettingsDialog

        SettingsDialog().exec()

    def open_logs() -> None:
        import os

        from atlas.utils.paths import get_log_dir

        os.startfile(str(get_log_dir()))  # noqa: S606 - fixed, known-safe path

    def reload_config() -> None:
        logger.info("Reload requested; not yet implemented (Phase 3)")

    def test_microphone() -> None:
        _test_microphone()

    def test_speech() -> None:
        _test_speech()

    tray = TrayApplication(
        on_enable_voice=enable_voice,
        on_disable_voice=disable_voice,
        on_test_microphone=test_microphone,
        on_test_speech=test_speech,
        on_open_settings=open_settings,
        on_open_logs=open_logs,
        on_reload=reload_config,
        on_exit=lambda: sys.exit(0),
    )
    return tray.run()


def main(argv: list[str] | None = None) -> int:
    # Window titles, application names, etc. can contain characters outside
    # the Windows console's legacy codepage (e.g. cp1252) - never let a
    # print() crash the CLI over an unencodable character.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    args = build_parser().parse_args(argv)

    if args.version:
        print(f"ATLAS {__version__}")
        return 0

    if args.diagnose:
        print(format_results(run_diagnostics()))
        return 0

    if args.list_plugins:
        app = Application()
        app.bootstrap()
        records = app.plugin_registry.all()
        if not records:
            print("No plugins discovered.")
        for record in records:
            print(f"{record.name}: {record.status.name} {record.reason}".rstrip())
        return 0

    if args.test_microphone:
        return _test_microphone()
    if args.test_speech:
        return _test_speech()
    if args.list_devices:
        return _list_devices()
    if args.list_monitors:
        return _list_monitors()
    if args.list_windows:
        return _list_windows()
    if args.reload:
        print(
            "Live reload requires signalling an already-running ATLAS process; "
            "not yet implemented (Phase 3)."
        )
        return 0

    app = Application()
    app.bootstrap()

    if args.tray:
        return _run_tray(app)

    print(
        "ATLAS foundation initialized. "
        "Use --tray to start the tray application, or --diagnose to run diagnostics."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
