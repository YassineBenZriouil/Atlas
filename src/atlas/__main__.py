"""Development CLI (Atlas.md section 70)."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable

from atlas import __version__
from atlas.application.app import Application
from atlas.diagnostics import CheckResult, format_results, run_diagnostics
from atlas.logging_setup import get_logger

logger = get_logger("cli")

_ANSI_COLOR_BY_STATUS = {
    "PASS": "\033[92m",  # green
    "WARN": "\033[93m",  # yellow
    "FAIL": "\033[91m",  # red
}
_ANSI_RESET = "\033[0m"


def _print_diagnostics(results: list[CheckResult]) -> None:
    """Colored PASS/WARN/FAIL when writing to a real terminal; plain text
    (no escape codes) when piped/redirected, so logs/output files stay
    clean."""
    if not sys.stdout.isatty():
        print(format_results(results))
        return

    for result in results:
        color = _ANSI_COLOR_BY_STATUS.get(result.status.name, "")
        line = f"{color}[{result.status.name}]{_ANSI_RESET} {result.name}"
        if result.detail:
            line += f" - {result.detail}"
        print(line)


# name -> help text; every command is `atlas <name>` (handlers in _COMMAND_HANDLERS).
COMMANDS: dict[str, str] = {
    "start": "Run ATLAS: open the window (starts the background core if needed)",
    "stop": "Stop the background core (voice stops too)",
    "status": "Show whether the core is running, voice state and speech engine",
    "reload": "Make the running core re-read its configuration",
    "console": "Type commands as text instead of speaking them",
    "diagnose": "Check what's working (colored PASS/WARN/FAIL)",
    "discover-apps": "Scan installed applications and add them to config",
    "list-plugins": "List plugins and why any are disabled",
    "list-devices": "List microphones",
    "list-monitors": "List monitors",
    "list-windows": "List open windows",
    "test-microphone": "Record 2 seconds to check the microphone",
    "test-speech": "Check the Vosk speech model loads",
    "spotify-login": "Connect a Spotify account",
    "spotify-logout": "Forget the stored Spotify account",
    "core": "Run the core in the foreground (what `atlas start` runs in the background)",
    "version": "Print the version",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atlas",
        description="ATLAS voice assistant. Run it with: atlas start",
    )
    parser.add_argument("--version", action="version", version=f"ATLAS {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for name, help_text in COMMANDS.items():
        subparsers.add_parser(name, help=help_text, description=help_text)
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
    from atlas.platform import get_backend

    for monitor in get_backend().monitor_manager().list_monitors():
        primary = " (primary)" if monitor.is_primary else ""
        print(f"#{monitor.index} {monitor.name}{primary} bounds={monitor.bounds}")
    return 0


def _list_windows() -> int:
    from atlas.platform import get_backend

    for window in get_backend().window_manager().list_windows():
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


def _discover_apps() -> int:
    from atlas.config.loader import save_config
    from atlas.platform import get_backend
    from atlas.platform.discovery import merge_discovered_apps
    from atlas.utils.paths import get_config_path

    app = Application()
    app.bootstrap()
    assert app.config is not None

    print("Scanning installed applications...")
    discovered = get_backend().discover_applications()
    result = merge_discovered_apps(app.config, discovered)

    if result.updated:
        print(f"\nFilled in a launch path for {len(result.updated)} already-configured app(s):")
        for name in sorted(result.updated):
            print(f"  {name}")

    if result.added:
        print(f"\nAdded {len(result.added)} new app(s):")
        for name in sorted(result.added):
            print(f"  {name}")

    if not result.updated and not result.added:
        print("\nNothing new to add - config is already up to date.")
        return 0

    save_config(get_config_path(), app.config)
    print(f"\nSaved to {get_config_path()}")
    return 0


def _spotify_login() -> int:
    import os

    from dotenv import load_dotenv

    from atlas.integrations.spotify.auth import SpotifyAuthError, SpotifyCredentials, run_login_flow

    load_dotenv()
    client_id = os.environ.get("ATLAS_SPOTIFY_CLIENT_ID", "")
    client_secret = os.environ.get("ATLAS_SPOTIFY_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("ATLAS_SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    if not client_id or not client_secret:
        print(
            "ATLAS_SPOTIFY_CLIENT_ID/ATLAS_SPOTIFY_CLIENT_SECRET are not set. "
            "Copy .env.example to .env, fill in your Spotify app's credentials "
            "(register one at https://developer.spotify.com), and try again."
        )
        return 1

    try:
        run_login_flow(SpotifyCredentials(client_id, client_secret, redirect_uri))
    except SpotifyAuthError as exc:
        print(f"Spotify sign-in failed: {exc}")
        return 1
    print("Spotify connected.")
    return 0


def _spotify_logout() -> int:
    from atlas.integrations.spotify.token_store import clear_refresh_token

    clear_refresh_token()
    print("Spotify credentials cleared.")
    return 0


def _run_console(app: Application) -> int:
    """Feeds typed text straight to Application.run_text_command - the
    same entry point speech recognition uses once it has transcribed
    something. Bypasses the microphone/wake/speech-engine entirely, so
    it's the fastest way to tell "the command doesn't work" apart from
    "ATLAS never heard the command in the first place"."""
    print("ATLAS text console - type a command, or 'exit' to quit.")
    print("Example: open brave")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text.lower() in ("exit", "quit"):
            break
        result = app.run_text_command(text)
        print(f"[{'OK' if result.success else 'FAIL'}] {result.message}")
    return 0


def _open_window() -> int:
    """`atlas start`: start the background core if needed and open the
    window. Closing the window leaves the core running."""
    from atlas.ui.window import run_window

    return run_window()


def _control_core(command: str) -> int:
    from atlas.service.client import CoreApiError, CoreUnavailableError, connect

    client = connect()
    if client is None:
        print("ATLAS core is not running. Start it with: atlas start")
        return 1
    try:
        if command == "stop":
            client.quit()
            print("ATLAS core stopped.")
        elif command == "reload":
            client.reload()
            print("Configuration reloaded.")
        else:
            status = client.status()
            voice = status["voice"]
            print(f"ATLAS {status['version']} core - pid {status['pid']}, port {client.info.port}")
            print(f"Voice: {'on' if voice['enabled'] else 'off'} {voice['error']}".rstrip())
            print(f"Speech providers: {' -> '.join(status['speech_providers'])}")
            print(f"Wake phrase: {status['wake_phrase']}")
    except (CoreUnavailableError, CoreApiError) as exc:
        print(exc)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    # Window titles, application names, etc. can contain characters outside
    # the Windows console's legacy codepage (e.g. cp1252) - never let a
    # print() crash the CLI over an unencodable character.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    from atlas.platform import PlatformNotSupportedError

    try:
        return _COMMAND_HANDLERS[args.command]()
    except PlatformNotSupportedError as exc:
        print(exc)
        return 1


def _version() -> int:
    print(f"ATLAS {__version__}")
    return 0


def _diagnose() -> int:
    _print_diagnostics(run_diagnostics())
    return 0


def _list_plugins() -> int:
    app = Application()
    app.bootstrap()
    records = app.plugin_registry.all()
    if not records:
        print("No plugins discovered.")
    for record in records:
        print(f"{record.name}: {record.status.name} {record.reason}".rstrip())
    return 0


def _console() -> int:
    app = Application()
    app.bootstrap()
    return _run_console(app)


def _core() -> int:
    from atlas.service.server import run_core

    return run_core()


_COMMAND_HANDLERS: dict[str, Callable[[], int]] = {
    "start": _open_window,
    "stop": lambda: _control_core("stop"),
    "status": lambda: _control_core("status"),
    "reload": lambda: _control_core("reload"),
    "console": _console,
    "diagnose": _diagnose,
    "discover-apps": _discover_apps,
    "list-plugins": _list_plugins,
    "list-devices": _list_devices,
    "list-monitors": _list_monitors,
    "list-windows": _list_windows,
    "test-microphone": _test_microphone,
    "test-speech": _test_speech,
    "spotify-login": _spotify_login,
    "spotify-logout": _spotify_logout,
    "core": _core,
    "version": _version,
}


if __name__ == "__main__":
    raise SystemExit(main())
