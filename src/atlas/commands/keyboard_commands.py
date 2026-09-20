"""Keyboard automation commands (Atlas.md section 24): press <key> / press
<key> <key> for combos. Key aliasing (control/ctrl, etc.) lives in
atlas.windows.keyboard and is shared with every other command that needs
to send keystrokes (browser shortcuts included)."""

from __future__ import annotations

from dataclasses import dataclass

from atlas.commands.command import (
    Command,
    CommandCategory,
    CommandContext,
    CommandResult,
    ValidationResult,
)
from atlas.commands.parser import CommandParser
from atlas.commands.registry import CommandRegistry
from atlas.windows.keyboard import KeyboardController, key_to_vk


def _keyboard(context: CommandContext) -> KeyboardController:
    return context.extra["keyboard_controller"]


@dataclass
class PressKeyCommand(Command):
    keys: tuple[str, ...]
    name = "press_key"
    category = CommandCategory.KEYBOARD

    def validate(self) -> ValidationResult:
        if not self.keys:
            return ValidationResult.failure("No key specified")
        try:
            for key in self.keys:
                key_to_vk(key)
        except ValueError as exc:
            return ValidationResult.failure(str(exc))
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        keyboard = _keyboard(context)
        if len(self.keys) == 1:
            keyboard.press_key(self.keys[0])
        else:
            keyboard.press_combo(list(self.keys))
        return CommandResult.ok(f"Pressed {' + '.join(self.keys)}")

    def describe(self) -> str:
        return f"Press {' + '.join(self.keys)}"


_COMMANDS: tuple[type[Command], ...] = (PressKeyCommand,)


def register(registry: CommandRegistry) -> None:
    for command_cls in _COMMANDS:
        if command_cls.name not in registry:
            registry.register(command_cls)


def _press_builder(groups: dict[str, str]) -> dict[str, tuple[str, ...]]:
    keys = tuple(groups["keys"].strip().split())
    return {"keys": keys}


def register_grammars(parser: CommandParser) -> None:
    parser.add_pattern("press_key", "press {keys}", _press_builder)
