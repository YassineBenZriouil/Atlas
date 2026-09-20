from tests.fixtures.fakes import FakeApplicationManager, FakeWindowManager

from atlas.commands.application_commands import (
    CloseApplicationCommand,
    FocusApplicationCommand,
    MaximizeApplicationCommand,
    MinimizeApplicationCommand,
    OpenApplicationCommand,
    RestoreApplicationCommand,
)
from atlas.commands.command import CommandContext
from atlas.config.defaults import default_config


def make_context():
    window_manager = FakeWindowManager()
    app_manager = FakeApplicationManager(window_manager)
    context = CommandContext(
        config=default_config(),
        extra={"application_manager": app_manager, "window_manager": window_manager},
    )
    return context, app_manager, window_manager


def test_open_launches_application():
    context, app_manager, _ = make_context()
    result = OpenApplicationCommand(application="brave").execute(context)
    assert result.success
    assert app_manager.is_running("brave")


def test_open_unknown_application_fails():
    context, _, _ = make_context()
    result = OpenApplicationCommand(application="unknownapp").execute(context)
    assert not result.success
    assert "not found" in result.message


def test_open_falls_back_to_configured_folder(tmp_path, monkeypatch):
    opened: list[str] = []
    monkeypatch.setattr(
        "atlas.commands.application_commands.os.startfile", lambda path: opened.append(path)
    )
    context, _, _ = make_context()
    context.config.folders["unknownapp"] = str(tmp_path)

    result = OpenApplicationCommand(application="unknownapp").execute(context)

    assert result.success
    assert opened == [str(tmp_path)]


def test_close_requires_running_application():
    context, _, _ = make_context()
    result = CloseApplicationCommand(application="brave").execute(context)
    assert not result.success


def test_close_terminates_running_application():
    context, app_manager, _ = make_context()
    app_manager.launch("brave")
    result = CloseApplicationCommand(application="brave").execute(context)
    assert result.success
    assert not app_manager.is_running("brave")


def test_focus_requires_running_application():
    context, _, _ = make_context()
    result = FocusApplicationCommand(application="brave").execute(context)
    assert not result.success


def test_focus_focuses_running_application():
    context, app_manager, window_manager = make_context()
    app_manager.launch("brave")
    result = FocusApplicationCommand(application="brave").execute(context)
    assert result.success
    assert ("focus", app_manager.running["brave"]) in window_manager.calls


def test_minimize_maximize_restore():
    context, app_manager, window_manager = make_context()
    app_manager.launch("brave")

    assert MinimizeApplicationCommand(application="brave").execute(context).success
    assert MaximizeApplicationCommand(application="brave").execute(context).success
    assert RestoreApplicationCommand(application="brave").execute(context).success

    kinds = [call[0] for call in window_manager.calls]
    assert "minimize" in kinds
    assert "maximize" in kinds
    assert "restore" in kinds


def test_validate_rejects_empty_application_name():
    result = OpenApplicationCommand(application="  ").validate()
    assert not result.ok
