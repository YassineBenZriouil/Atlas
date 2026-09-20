from tests.fixtures.fakes import FakeKeyboardController

from atlas.commands.command import CommandContext
from atlas.commands.keyboard_commands import PressKeyCommand


def make_context(keyboard: FakeKeyboardController) -> CommandContext:
    return CommandContext(extra={"keyboard_controller": keyboard})


def test_press_single_key():
    keyboard = FakeKeyboardController()
    result = PressKeyCommand(keys=("enter",)).execute(make_context(keyboard))
    assert result.success
    assert keyboard.pressed == ["enter"]


def test_press_combo():
    keyboard = FakeKeyboardController()
    result = PressKeyCommand(keys=("control", "c")).execute(make_context(keyboard))
    assert result.success
    assert keyboard.combos == [["control", "c"]]


def test_validate_rejects_empty_keys():
    assert not PressKeyCommand(keys=()).validate().ok


def test_validate_rejects_unknown_key():
    assert not PressKeyCommand(keys=("not_a_real_key",)).validate().ok
