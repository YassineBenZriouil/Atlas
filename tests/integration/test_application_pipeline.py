from atlas.application.app import Application
from atlas.application.state import AtlasState


def test_status_command_end_to_end():
    app = Application()
    app.bootstrap()
    result = app.run_text_command("atlas status")
    assert result.success
    assert app.state_machine.state is AtlasState.SLEEPING


def test_unknown_command_recovers_to_sleeping():
    app = Application()
    app.bootstrap()
    result = app.run_text_command("do a backflip")
    assert not result.success
    assert app.state_machine.state is AtlasState.SLEEPING


def test_help_lists_builtin_commands():
    app = Application()
    app.bootstrap()
    result = app.run_text_command("atlas help")
    assert result.success
    assert "atlas_status" in result.data["commands"]


def test_test_command_reports_pipeline_operational():
    app = Application()
    app.bootstrap()
    result = app.run_text_command("atlas test")
    assert result.success
    assert "operational" in result.message
