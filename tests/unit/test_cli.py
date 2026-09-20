from tests.fixtures.fakes import (
    FakeApplicationManager,
    FakeKeyboardController,
    FakeMonitorManager,
    FakeMouseController,
    FakeSystemController,
    FakeWindowManager,
)

from atlas.__main__ import _run_console, build_parser, main
from atlas.application.app import Application


def make_fake_app() -> Application:
    window_manager = FakeWindowManager()
    app = Application(
        window_manager=window_manager,
        monitor_manager=FakeMonitorManager(),
        keyboard_controller=FakeKeyboardController(),
        mouse_controller=FakeMouseController(),
        system_controller=FakeSystemController(),
        application_manager=FakeApplicationManager(window_manager),
    )
    app.bootstrap()
    return app


def test_version_flag(capsys):
    exit_code = main(["--version"])
    assert exit_code == 0
    assert "ATLAS" in capsys.readouterr().out


def test_diagnose_flag_runs_without_crashing(capsys):
    exit_code = main(["--diagnose"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Python" in out


def test_list_monitors_does_not_crash(capsys):
    exit_code = main(["--list-monitors"])
    assert exit_code == 0


def test_parser_accepts_all_documented_flags():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--test-microphone",
            "--test-speech",
            "--list-devices",
            "--list-monitors",
            "--list-windows",
            "--list-plugins",
            "--reload",
            "--tray",
            "--console",
            "--spotify-login",
            "--spotify-logout",
        ]
    )
    assert args.test_microphone
    assert args.tray
    assert args.console


def test_console_mode_runs_commands_against_fakes(monkeypatch, capsys):
    app = make_fake_app()
    inputs = iter(["open brave", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    exit_code = _run_console(app)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "[OK] Opening brave" in out


def test_console_mode_reports_failures(monkeypatch, capsys):
    app = make_fake_app()
    inputs = iter(["do a backflip", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    _run_console(app)

    out = capsys.readouterr().out
    assert "[FAIL]" in out


def test_console_mode_handles_eof_gracefully(monkeypatch, capsys):
    app = make_fake_app()

    def raise_eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)

    exit_code = _run_console(app)

    assert exit_code == 0
