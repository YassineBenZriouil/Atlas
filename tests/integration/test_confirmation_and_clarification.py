"""Application-level flows using injected fakes (Atlas.md sections 28-29,
40-41) - never touches real Win32 APIs, and specifically never lets a test
actually shut down or restart the machine."""

from tests.fixtures.fakes import (
    FakeApplicationManager,
    FakeKeyboardController,
    FakeMonitorManager,
    FakeMouseController,
    FakeSystemController,
    FakeWindowManager,
)

from atlas.application.app import Application


def make_app() -> tuple[Application, FakeSystemController, FakeWindowManager]:
    window_manager = FakeWindowManager()
    system = FakeSystemController()
    app = Application(
        window_manager=window_manager,
        monitor_manager=FakeMonitorManager(),
        keyboard_controller=FakeKeyboardController(),
        mouse_controller=FakeMouseController(),
        system_controller=system,
        application_manager=FakeApplicationManager(window_manager),
    )
    app.bootstrap()
    return app, system, window_manager


def test_shutdown_requires_confirmation_and_never_executes_without_it():
    app, system, _ = make_app()

    result = app.run_text_command("shutdown computer")
    assert not result.success
    assert result.data.get("awaiting_confirmation") is True
    assert system.shutdown_called is False

    result2 = app.run_text_command("banana")
    assert not result2.success
    assert system.shutdown_called is False


def test_shutdown_executes_only_after_explicit_confirm():
    app, system, _ = make_app()

    app.run_text_command("shutdown computer")
    result = app.run_text_command("confirm")

    assert result.success
    assert system.shutdown_called is True


def test_restart_also_requires_confirmation():
    app, system, _ = make_app()

    app.run_text_command("restart computer")
    assert system.restart_called is False

    app.run_text_command("confirm")
    assert system.restart_called is True


def test_mute_never_requires_confirmation():
    app, system, _ = make_app()
    result = app.run_text_command("mute")
    assert result.success
    assert system.muted


def test_move_bare_asks_which_monitor_then_executes():
    app, _, _ = make_app()
    app.run_text_command("open brave")

    result = app.run_text_command("move brave")
    assert result.success
    assert result.message == "Which monitor?"

    result2 = app.run_text_command("two")
    assert result2.success
    assert "monitor 2" in result2.message


def test_move_bare_clarification_can_be_abandoned():
    app, _, _ = make_app()
    app.run_text_command("open brave")
    app.run_text_command("move brave")

    result = app.run_text_command("banana")

    assert not result.success
    assert "cancelled" in result.message.lower()


def test_state_machine_returns_to_sleeping_after_every_flow():
    from atlas.application.state import AtlasState

    app, _, _ = make_app()
    app.run_text_command("shutdown computer")
    assert app.state_machine.state is AtlasState.SLEEPING
    app.run_text_command("confirm")
    assert app.state_machine.state is AtlasState.SLEEPING

    app.run_text_command("open brave")
    app.run_text_command("move brave")
    assert app.state_machine.state is AtlasState.SLEEPING
    app.run_text_command("two")
    assert app.state_machine.state is AtlasState.SLEEPING
