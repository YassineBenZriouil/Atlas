"""Window placement commands (Atlas.md sections 20-21): move to monitor,
resize, move left/right/up/down. Also implements the one clarification flow
the spec calls out by name (sections 28-29): a bare "move <application>"
with no monitor/direction asks "Which monitor?" instead of guessing."""

from __future__ import annotations

import re
from dataclasses import dataclass

from atlas.commands.command import (
    Command,
    CommandCategory,
    CommandContext,
    CommandResult,
    ValidationResult,
)
from atlas.commands.parser import CommandParser, NeedsClarification, ParamBuilder
from atlas.commands.registry import CommandRegistry
from atlas.utils.strings import words_to_numbers
from atlas.windows.applications import ApplicationManager
from atlas.windows.monitors import MonitorManager
from atlas.windows.windows import Rect, WindowManager

_DIRECTIONS = ("left", "right", "up", "down")
_MOVE_STEP = 80


def _managers(context: CommandContext) -> tuple[ApplicationManager, WindowManager, MonitorManager]:
    return (
        context.extra["application_manager"],
        context.extra["window_manager"],
        context.extra["monitor_manager"],
    )


@dataclass
class MoveToMonitorCommand(Command):
    """`monitor` is a digit string, or the literal "primary" for phrasings
    like "put VS Code on the main monitor" - resolution to an actual
    Monitor happens here, not at parse time."""

    application: str
    monitor: str
    name = "move_to_monitor"
    category = CommandCategory.WINDOW

    def validate(self) -> ValidationResult:
        if not self.application.strip():
            return ValidationResult.failure("No application specified")
        if self.monitor != "primary" and not self.monitor.isdigit():
            return ValidationResult.failure(f"Invalid monitor: {self.monitor}")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        app_manager, window_manager, monitor_manager = _managers(context)
        windows = app_manager.windows_for(self.application)
        if not windows:
            return CommandResult.fail(f"{self.application} is not running")

        target = (
            monitor_manager.get_primary_monitor()
            if self.monitor == "primary"
            else monitor_manager.get_monitor(int(self.monitor))
        )
        if target is None:
            return CommandResult.fail(f"Monitor {self.monitor} was not found")

        window = windows[0]
        area = target.work_area
        window_manager.move_window(window, Rect(area.x, area.y, area.width, area.height))
        window_manager.focus_window(window)
        label = "the main monitor" if self.monitor == "primary" else f"monitor {self.monitor}"
        return CommandResult.ok(f"Moved {self.application} to {label}")

    def describe(self) -> str:
        return f"Move {self.application} to monitor {self.monitor}"


@dataclass
class ResizeApplicationCommand(Command):
    application: str
    width: int
    height: int
    name = "resize_application"
    category = CommandCategory.WINDOW

    def validate(self) -> ValidationResult:
        if not self.application.strip():
            return ValidationResult.failure("No application specified")
        if self.width <= 0 or self.height <= 0:
            return ValidationResult.failure("Width and height must be positive")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        app_manager, window_manager, _ = _managers(context)
        windows = app_manager.windows_for(self.application)
        if not windows:
            return CommandResult.fail(f"{self.application} is not running")
        window_manager.resize_window(windows[0], self.width, self.height)
        return CommandResult.ok(f"Resized {self.application} to {self.width} by {self.height}")

    def describe(self) -> str:
        return f"Resize {self.application} to {self.width}x{self.height}"


@dataclass
class MoveDirectionCommand(Command):
    application: str
    direction: str
    name = "move_direction"
    category = CommandCategory.WINDOW

    def validate(self) -> ValidationResult:
        if not self.application.strip():
            return ValidationResult.failure("No application specified")
        if self.direction not in _DIRECTIONS:
            return ValidationResult.failure(f"Unknown direction: {self.direction}")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        app_manager, window_manager, _ = _managers(context)
        windows = app_manager.windows_for(self.application)
        if not windows:
            return CommandResult.fail(f"{self.application} is not running")

        window = windows[0]
        rect = window_manager.get_window_rect(window)
        dx, dy = {
            "left": (-_MOVE_STEP, 0),
            "right": (_MOVE_STEP, 0),
            "up": (0, -_MOVE_STEP),
            "down": (0, _MOVE_STEP),
        }[self.direction]
        window_manager.move_window(window, Rect(rect.x + dx, rect.y + dy, rect.width, rect.height))
        return CommandResult.ok(f"Moved {self.application} {self.direction}")

    def describe(self) -> str:
        return f"Move {self.application} {self.direction}"


_COMMANDS: tuple[type[Command], ...] = (
    MoveToMonitorCommand,
    ResizeApplicationCommand,
    MoveDirectionCommand,
)


def register(registry: CommandRegistry) -> None:
    for command_cls in _COMMANDS:
        if command_cls.name not in registry:
            registry.register(command_cls)


def _numeric_monitor_builder(groups: dict[str, str]) -> dict[str, str]:
    application = groups["application"].strip()
    digits = re.sub(r"[^0-9]", "", groups["monitor"])
    if not digits:
        raise ValueError(f"Invalid monitor: {groups['monitor']}")
    return {"application": application, "monitor": digits}


def _primary_monitor_builder(groups: dict[str, str]) -> dict[str, str]:
    return {"application": groups["application"].strip(), "monitor": "primary"}


def _resize_builder(groups: dict[str, str]) -> dict[str, object]:
    application = groups["application"].strip()
    width_digits = re.sub(r"[^0-9]", "", groups["width"])
    height_digits = re.sub(r"[^0-9]", "", groups["height"])
    if not width_digits or not height_digits:
        raise ValueError("Width and height must be numbers")
    return {"application": application, "width": int(width_digits), "height": int(height_digits)}


def _make_direction_builder(direction: str) -> ParamBuilder:
    def builder(groups: dict[str, str]) -> dict[str, object]:
        return {"application": groups["application"].strip(), "direction": direction}

    return builder


def register_grammars(parser: CommandParser) -> None:
    for phrase in (
        "move {application} to monitor {monitor}",
        "put {application} on monitor {monitor}",
        "send {application} to screen {monitor}",
        "move {application} onto display {monitor}",
        "move {application} to screen {monitor}",
        "put {application} on screen {monitor}",
    ):
        parser.add_pattern("move_to_monitor", phrase, _numeric_monitor_builder)

    for phrase in (
        "put {application} on the main monitor",
        "move {application} to the main monitor",
        "put {application} on the primary monitor",
    ):
        parser.add_pattern("move_to_monitor", phrase, _primary_monitor_builder)

    parser.add_pattern(
        "resize_application", "resize {application} to {width} by {height}", _resize_builder
    )

    for direction in _DIRECTIONS:
        parser.add_pattern(
            "move_direction",
            f"move {{application}} {direction}",
            _make_direction_builder(direction),
        )

    parser.add_custom_matcher(_bare_move_matcher)


_BARE_MOVE_RE = re.compile(r"move (?P<application>.+)")


def _bare_move_matcher(normalized_text: str) -> NeedsClarification | None:
    match = _BARE_MOVE_RE.fullmatch(normalized_text)
    if match is None:
        return None
    application = match.group("application").strip()

    def resolve(follow_up: str) -> Command | None:
        digits = re.sub(r"[^0-9]", "", words_to_numbers(follow_up))
        if not digits:
            return None
        return MoveToMonitorCommand(application=application, monitor=digits)

    return NeedsClarification(
        command_name="move_to_monitor",
        prompt="Which monitor?",
        resolve=resolve,
    )
