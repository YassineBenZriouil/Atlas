from tests.fixtures.fakes import FakeApplicationManager, FakeMonitorManager, FakeWindowManager

from atlas.commands.command import CommandContext
from atlas.commands.parser import CommandParser
from atlas.commands.registry import CommandRegistry
from atlas.commands.window_commands import (
    MoveDirectionCommand,
    MoveToMonitorCommand,
    ResizeApplicationCommand,
    _bare_move_matcher,
    register,
    register_grammars,
)
from atlas.config.defaults import default_config
from atlas.windows.windows import Rect


def make_context():
    window_manager = FakeWindowManager()
    app_manager = FakeApplicationManager(window_manager)
    monitor_manager = FakeMonitorManager()
    context = CommandContext(
        config=default_config(),
        extra={
            "application_manager": app_manager,
            "window_manager": window_manager,
            "monitor_manager": monitor_manager,
        },
    )
    return context, app_manager, window_manager, monitor_manager


def test_move_to_monitor_requires_running_application():
    context, *_ = make_context()
    result = MoveToMonitorCommand(application="brave", monitor="2").execute(context)
    assert not result.success


def test_move_to_monitor_moves_and_focuses():
    context, app_manager, window_manager, _ = make_context()
    app_manager.launch("brave")

    result = MoveToMonitorCommand(application="brave", monitor="2").execute(context)

    assert result.success
    window = app_manager.running["brave"]
    assert window_manager.rects[window.handle] == Rect(1920, 0, 1280, 984)
    assert ("focus", window) in window_manager.calls


def test_move_to_unknown_monitor_fails():
    context, app_manager, *_ = make_context()
    app_manager.launch("brave")
    result = MoveToMonitorCommand(application="brave", monitor="99").execute(context)
    assert not result.success
    assert "not found" in result.message


def test_move_to_primary_monitor():
    context, app_manager, window_manager, _ = make_context()
    app_manager.launch("brave")

    result = MoveToMonitorCommand(application="brave", monitor="primary").execute(context)

    assert result.success
    window = app_manager.running["brave"]
    assert window_manager.rects[window.handle] == Rect(0, 0, 1920, 1040)


def test_resize_application():
    context, app_manager, window_manager, _ = make_context()
    app_manager.launch("brave")

    result = ResizeApplicationCommand(application="brave", width=800, height=600).execute(context)

    assert result.success
    window = app_manager.running["brave"]
    rect = window_manager.rects[window.handle]
    assert (rect.width, rect.height) == (800, 600)


def test_resize_rejects_non_positive_dimensions():
    result = ResizeApplicationCommand(application="brave", width=0, height=600).validate()
    assert not result.ok


def test_move_direction_moves_relative():
    context, app_manager, window_manager, _ = make_context()
    app_manager.launch("brave")
    window = app_manager.running["brave"]
    before = window_manager.rects[window.handle]

    result = MoveDirectionCommand(application="brave", direction="right").execute(context)

    assert result.success
    after = window_manager.rects[window.handle]
    assert after.x == before.x + 80
    assert after.y == before.y


def test_move_direction_rejects_unknown_direction():
    result = MoveDirectionCommand(application="brave", direction="sideways").validate()
    assert not result.ok


def test_bare_move_asks_for_monitor():
    outcome = _bare_move_matcher("move brave")
    assert outcome is not None
    assert outcome.prompt == "Which monitor?"

    resolved = outcome.resolve("two")
    assert isinstance(resolved, MoveToMonitorCommand)
    assert resolved.application == "brave"
    assert resolved.monitor == "2"


def test_bare_move_resolve_returns_none_for_non_number():
    outcome = _bare_move_matcher("move brave")
    assert outcome is not None
    assert outcome.resolve("banana") is None


def test_full_move_command_takes_priority_over_bare_clarification():
    """The custom bare-move matcher's regex alone would match "move brave to
    monitor 2" too - it's the parser trying pattern grammars first that
    prevents the ambiguity, so that ordering is what this test protects."""
    registry = CommandRegistry()
    register(registry)
    parser = CommandParser(registry)
    register_grammars(parser)

    result = parser.parse("move brave to monitor 2")

    assert result.ok
    assert not result.needs_clarification
    assert isinstance(result.command, MoveToMonitorCommand)
    assert result.command.monitor == "2"
