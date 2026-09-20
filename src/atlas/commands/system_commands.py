"""System-level commands (Atlas.md section 22): volume, mute, lock, sleep,
shutdown/restart (gated by atlas.security.permissions - their command
`name`s match the entries in DANGEROUS_COMMAND_NAMES exactly), screenshot."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from atlas.commands.command import (
    Command,
    CommandCategory,
    CommandContext,
    CommandResult,
    ValidationResult,
)
from atlas.commands.matcher import Grammar
from atlas.commands.parser import CommandParser
from atlas.commands.registry import CommandRegistry
from atlas.utils.paths import get_app_data_dir
from atlas.windows.system import SystemController


def _system(context: CommandContext) -> SystemController:
    return context.extra["system_controller"]


class MuteCommand(Command):
    name = "mute"
    category = CommandCategory.SYSTEM

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        _system(context).mute()
        return CommandResult.ok("Muted")

    def describe(self) -> str:
        return "Mute system volume"


class UnmuteCommand(Command):
    name = "unmute"
    category = CommandCategory.SYSTEM

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        _system(context).unmute()
        return CommandResult.ok("Unmuted")

    def describe(self) -> str:
        return "Unmute system volume"


class VolumeUpCommand(Command):
    name = "volume_up"
    category = CommandCategory.SYSTEM

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        _system(context).volume_up()
        return CommandResult.ok("Volume up")

    def describe(self) -> str:
        return "Increase volume"


class VolumeDownCommand(Command):
    name = "volume_down"
    category = CommandCategory.SYSTEM

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        _system(context).volume_down()
        return CommandResult.ok("Volume down")

    def describe(self) -> str:
        return "Decrease volume"


@dataclass
class SetVolumeCommand(Command):
    level: int
    name = "set_volume"
    category = CommandCategory.SYSTEM

    def validate(self) -> ValidationResult:
        if not 0 <= self.level <= 100:
            return ValidationResult.failure("Volume must be between 0 and 100")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        _system(context).set_volume(self.level)
        return CommandResult.ok(f"Volume set to {self.level}")

    def describe(self) -> str:
        return f"Set volume to {self.level}"


class LockComputerCommand(Command):
    name = "lock_computer"
    category = CommandCategory.SYSTEM

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        _system(context).lock()
        return CommandResult.ok("Locking computer")

    def describe(self) -> str:
        return "Lock the computer"


class SleepComputerCommand(Command):
    name = "sleep_computer"
    category = CommandCategory.SYSTEM

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        _system(context).sleep()
        return CommandResult.ok("Sleeping computer")

    def describe(self) -> str:
        return "Put the computer to sleep"


class ShutdownComputerCommand(Command):
    name = "shutdown_computer"
    category = CommandCategory.SYSTEM

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        _system(context).shutdown()
        return CommandResult.ok("Shutting down")

    def describe(self) -> str:
        return "Shut down the computer"


class RestartComputerCommand(Command):
    name = "restart_computer"
    category = CommandCategory.SYSTEM

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        _system(context).restart()
        return CommandResult.ok("Restarting")

    def describe(self) -> str:
        return "Restart the computer"


class TakeScreenshotCommand(Command):
    name = "take_screenshot"
    category = CommandCategory.SYSTEM

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        destination = (
            get_app_data_dir() / "screenshots" / f"{datetime.now():%Y%m%d-%H%M%S}.png"
        )
        path = _system(context).take_screenshot(destination)
        return CommandResult.ok(f"Screenshot saved to {path}", path=str(path))

    def describe(self) -> str:
        return "Take a screenshot"


_COMMANDS: tuple[type[Command], ...] = (
    MuteCommand,
    UnmuteCommand,
    VolumeUpCommand,
    VolumeDownCommand,
    SetVolumeCommand,
    LockComputerCommand,
    SleepComputerCommand,
    ShutdownComputerCommand,
    RestartComputerCommand,
    TakeScreenshotCommand,
)


def register(registry: CommandRegistry) -> None:
    for command_cls in _COMMANDS:
        if command_cls.name not in registry:
            registry.register(command_cls)


def _volume_level_builder(groups: dict[str, str]) -> dict[str, int]:
    digits = re.sub(r"[^0-9]", "", groups["level"])
    if not digits:
        raise ValueError("Volume level must be a number")
    return {"level": int(digits)}


def register_grammars(parser: CommandParser) -> None:
    parser.add_grammar(Grammar("mute", ("mute",)))
    parser.add_grammar(Grammar("unmute", ("unmute",)))
    parser.add_grammar(
        Grammar("volume_up", ("volume up", "increase volume", "turn up the volume"))
    )
    parser.add_grammar(
        Grammar("volume_down", ("volume down", "decrease volume", "turn down the volume"))
    )
    parser.add_grammar(Grammar("lock_computer", ("lock the computer", "lock computer")))
    parser.add_grammar(Grammar("sleep_computer", ("sleep the computer", "sleep computer")))
    parser.add_grammar(
        Grammar(
            "shutdown_computer",
            (
                "shutdown the computer",
                "shutdown computer",
                "shut down the computer",
                "shut down computer",
            ),
        )
    )
    parser.add_grammar(Grammar("restart_computer", ("restart the computer", "restart computer")))
    parser.add_grammar(Grammar("take_screenshot", ("take a screenshot", "take screenshot")))

    for phrase in ("set volume to {level}", "volume {level}"):
        parser.add_pattern("set_volume", phrase, _volume_level_builder)
