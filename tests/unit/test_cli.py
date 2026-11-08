import pytest
from tests.fixtures.fakes import (
    FakeApplicationManager,
    FakeKeyboardController,
    FakeMonitorManager,
    FakeMouseController,
    FakeSystemController,
    FakeWindowManager,
)

from atlas.__main__ import (
    _COMMAND_HANDLERS,
    COMMANDS,
    _print_diagnostics,
    _run_console,
    build_parser,
    main,
)
from atlas.application.app import Application
from atlas.diagnostics import CheckResult, CheckStatus


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


def test_version_command_and_flag(capsys):
    assert main(["version"]) == 0
    assert "ATLAS" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "ATLAS" in capsys.readouterr().out


def test_bare_atlas_lists_commands(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "atlas start" in out
    for name in COMMANDS:
        assert name in out


def test_every_command_has_a_handler():
    assert COMMANDS.keys() == _COMMAND_HANDLERS.keys()
    parser = build_parser()
    for name in COMMANDS:
        assert parser.parse_args([name]).command == name


def test_old_flag_style_is_rejected():
    with pytest.raises(SystemExit):
        main(["--start"])


def test_diagnose_runs_without_crashing(capsys):
    assert main(["diagnose"]) == 0
    assert "Python" in capsys.readouterr().out


def test_list_monitors_does_not_crash():
    assert main(["list-monitors"]) == 0


def test_stop_and_status_without_core_point_to_atlas_start(capsys):
    assert main(["status"]) == 1
    assert "atlas start" in capsys.readouterr().out


def test_detached_core_launches_the_core_subcommand(monkeypatch):
    from atlas.service import client

    launched: list[list[str]] = []
    monkeypatch.setattr(client.subprocess, "Popen", lambda cmd, **kw: launched.append(cmd))
    client.start_core_detached()
    assert launched[0][-3:] == ["-m", "atlas", "core"]


def test_print_diagnostics_plain_when_not_a_tty(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    results = [
        CheckResult("Thing A", CheckStatus.PASS),
        CheckResult("Thing B", CheckStatus.FAIL, "broken"),
    ]

    _print_diagnostics(results)

    out = capsys.readouterr().out
    assert "\033[" not in out
    assert "[PASS] Thing A" in out
    assert "[FAIL] Thing B - broken" in out


def test_print_diagnostics_colored_when_a_tty(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    results = [
        CheckResult("Thing A", CheckStatus.PASS),
        CheckResult("Thing B", CheckStatus.WARN, "meh"),
        CheckResult("Thing C", CheckStatus.FAIL, "broken"),
    ]

    _print_diagnostics(results)

    out = capsys.readouterr().out
    assert "\033[92m[PASS]\033[0m Thing A" in out
    assert "\033[93m[WARN]\033[0m Thing B - meh" in out
    assert "\033[91m[FAIL]\033[0m Thing C - broken" in out


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
