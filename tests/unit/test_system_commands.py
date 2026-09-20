from tests.fixtures.fakes import FakeSystemController

from atlas.commands.command import CommandContext
from atlas.commands.system_commands import (
    LockComputerCommand,
    MuteCommand,
    RestartComputerCommand,
    SetVolumeCommand,
    ShutdownComputerCommand,
    SleepComputerCommand,
    TakeScreenshotCommand,
    UnmuteCommand,
    VolumeDownCommand,
    VolumeUpCommand,
)


def make_context(system: FakeSystemController) -> CommandContext:
    return CommandContext(extra={"system_controller": system})


def test_mute_and_unmute():
    system = FakeSystemController()
    context = make_context(system)

    assert MuteCommand().execute(context).success
    assert system.muted

    assert UnmuteCommand().execute(context).success
    assert not system.muted


def test_volume_up_and_down():
    system = FakeSystemController()
    context = make_context(system)
    system.volume = 50

    VolumeUpCommand().execute(context)
    assert system.volume == 60

    VolumeDownCommand().execute(context)
    assert system.volume == 50


def test_set_volume_within_bounds():
    system = FakeSystemController()
    context = make_context(system)

    result = SetVolumeCommand(level=30).execute(context)

    assert result.success
    assert system.volume == 30


def test_set_volume_rejects_out_of_range():
    assert not SetVolumeCommand(level=150).validate().ok
    assert not SetVolumeCommand(level=-1).validate().ok


def test_lock_and_sleep():
    system = FakeSystemController()
    context = make_context(system)

    assert LockComputerCommand().execute(context).success
    assert ("lock",) in system.calls

    assert SleepComputerCommand().execute(context).success
    assert ("sleep",) in system.calls


def test_shutdown_and_restart_call_through():
    """Command-level execute() has no confirmation logic of its own - that
    gate lives in the dispatcher (see test_dispatcher.py / the Application
    confirmation-flow integration test). This only proves the command
    itself calls the right controller method."""
    system = FakeSystemController()
    context = make_context(system)

    ShutdownComputerCommand().execute(context)
    assert system.shutdown_called

    system2 = FakeSystemController()
    RestartComputerCommand().execute(make_context(system2))
    assert system2.restart_called


def test_take_screenshot(tmp_path):
    system = FakeSystemController()
    context = make_context(system)

    result = TakeScreenshotCommand().execute(context)

    assert result.success
    assert system.calls[0][0] == "screenshot"
