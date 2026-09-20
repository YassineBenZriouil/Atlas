"""Development CLI (Atlas.md section 70)."""

from __future__ import annotations

import argparse
import sys

from atlas import __version__
from atlas.application.app import Application
from atlas.diagnostics import format_results, run_diagnostics


def _not_yet_implemented(feature: str) -> int:
    print(f"{feature} is implemented in Phase 2.")
    return 0


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


def main(argv: list[str] | None = None) -> int:
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
        return _not_yet_implemented("Microphone testing")
    if args.test_speech:
        return _not_yet_implemented("Speech engine testing")
    if args.list_devices:
        return _not_yet_implemented("Audio device listing")
    if args.list_monitors:
        return _not_yet_implemented("Monitor listing")
    if args.list_windows:
        return _not_yet_implemented("Window listing")
    if args.reload:
        return _not_yet_implemented("Live reload")

    app = Application()
    app.bootstrap()

    if args.tray:
        from atlas.ui.tray import TrayApplication

        tray = TrayApplication(on_exit=lambda: sys.exit(0))
        return tray.run()

    print(
        "ATLAS foundation initialized. "
        "Use --tray to start the tray application, or --diagnose to run diagnostics."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
