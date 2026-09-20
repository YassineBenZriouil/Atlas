"""Application lifecycle commands (Atlas.md sections 18, 21): open/close/
focus/switch/minimize/maximize/restore <application>.

Parsing only ever produces a raw application name string - alias/path
resolution happens here, in execute(), via the injected ApplicationManager,
so an unresolvable name surfaces as a normal execution failure
("'photoshop' was not found") rather than a parser guess."""

from __future__ import annotations

import os
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
from atlas.integrations.filesystem.folders import resolve_folder
from atlas.windows.applications import ApplicationManager, ApplicationNotFoundError
from atlas.windows.windows import WindowHandle, WindowManager


def _managers(context: CommandContext) -> tuple[ApplicationManager, WindowManager]:
    return context.extra["application_manager"], context.extra["window_manager"]


def _display_name(app_manager: ApplicationManager, application: str) -> str:
    """The fuzzy alias fallback (Atlas.md section 63) means what the user
    said and what ATLAS actually resolved can differ (e.g. a misheard
    "vs cold" resolving to "vscode") - success messages should echo the
    resolved name, not the raw possibly-misheard text, so the response
    doesn't read as if it repeated the mistake back."""
    info = app_manager.resolve_alias(application)
    return info.alias if info is not None else application


def _require_window(context: CommandContext, application: str) -> WindowHandle | CommandResult:
    app_manager, _ = _managers(context)
    windows = app_manager.windows_for(application)
    if not windows:
        return CommandResult.fail(f"{application} is not running")
    return windows[0]


@dataclass
class OpenApplicationCommand(Command):
    """"open X" covers both applications and folders (Atlas.md sections 18,
    23) - there is exactly one "open X" grammar, and application resolution
    is tried first, falling back to a known/configured folder. Two
    competing commands bound to the identical "open {x}" text would be
    unreachable for one of them, so this is deliberately one command."""

    application: str
    name = "open_application"
    category = CommandCategory.APPLICATION

    def validate(self) -> ValidationResult:
        if not self.application.strip():
            return ValidationResult.failure("No application specified")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        app_manager, _ = _managers(context)
        try:
            app_manager.launch(self.application)
            name = _display_name(app_manager, self.application)
            return CommandResult.ok(f"Opening {name}", application=name)
        except ApplicationNotFoundError:
            pass

        folder = resolve_folder(context.config, self.application)
        if folder is not None:
            os.startfile(str(folder))  # noqa: S606 - resolved, existing directory only
            return CommandResult.ok(f"Opening {self.application}", folder=str(folder))

        return CommandResult.fail(f"'{self.application}' was not found")

    def describe(self) -> str:
        return f"Open {self.application}"


@dataclass
class CloseApplicationCommand(Command):
    application: str
    name = "close_application"
    category = CommandCategory.APPLICATION

    def validate(self) -> ValidationResult:
        if not self.application.strip():
            return ValidationResult.failure("No application specified")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        app_manager, _ = _managers(context)
        if not app_manager.is_running(self.application):
            return CommandResult.fail(f"{self.application} is not running")
        app_manager.terminate(self.application)
        return CommandResult.ok(f"Closing {_display_name(app_manager, self.application)}")

    def describe(self) -> str:
        return f"Close {self.application}"


@dataclass
class FocusApplicationCommand(Command):
    """Also reached via "switch to <application>" - same behavior, same
    command, two grammar phrasings."""

    application: str
    name = "focus_application"
    category = CommandCategory.WINDOW

    def validate(self) -> ValidationResult:
        if not self.application.strip():
            return ValidationResult.failure("No application specified")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _require_window(context, self.application)
        if isinstance(window, CommandResult):
            return window
        app_manager, window_manager = _managers(context)
        window_manager.focus_window(window)
        return CommandResult.ok(f"Switched to {_display_name(app_manager, self.application)}")

    def describe(self) -> str:
        return f"Switch to {self.application}"


@dataclass
class MinimizeApplicationCommand(Command):
    application: str
    name = "minimize_application"
    category = CommandCategory.WINDOW

    def validate(self) -> ValidationResult:
        if not self.application.strip():
            return ValidationResult.failure("No application specified")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _require_window(context, self.application)
        if isinstance(window, CommandResult):
            return window
        app_manager, window_manager = _managers(context)
        window_manager.minimize_window(window)
        return CommandResult.ok(f"Minimized {_display_name(app_manager, self.application)}")

    def describe(self) -> str:
        return f"Minimize {self.application}"


@dataclass
class MaximizeApplicationCommand(Command):
    application: str
    name = "maximize_application"
    category = CommandCategory.WINDOW

    def validate(self) -> ValidationResult:
        if not self.application.strip():
            return ValidationResult.failure("No application specified")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _require_window(context, self.application)
        if isinstance(window, CommandResult):
            return window
        app_manager, window_manager = _managers(context)
        window_manager.maximize_window(window)
        return CommandResult.ok(f"Maximized {_display_name(app_manager, self.application)}")

    def describe(self) -> str:
        return f"Maximize {self.application}"


@dataclass
class RestoreApplicationCommand(Command):
    application: str
    name = "restore_application"
    category = CommandCategory.WINDOW

    def validate(self) -> ValidationResult:
        if not self.application.strip():
            return ValidationResult.failure("No application specified")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _require_window(context, self.application)
        if isinstance(window, CommandResult):
            return window
        app_manager, window_manager = _managers(context)
        window_manager.restore_window(window)
        return CommandResult.ok(f"Restored {_display_name(app_manager, self.application)}")

    def describe(self) -> str:
        return f"Restore {self.application}"


_COMMANDS: tuple[type[Command], ...] = (
    OpenApplicationCommand,
    CloseApplicationCommand,
    FocusApplicationCommand,
    MinimizeApplicationCommand,
    MaximizeApplicationCommand,
    RestoreApplicationCommand,
)


def register(registry: CommandRegistry) -> None:
    for command_cls in _COMMANDS:
        if command_cls.name not in registry:
            registry.register(command_cls)


def _application_only(groups: dict[str, str]) -> dict[str, str]:
    return {"application": groups["application"].strip()}


def register_grammars(parser: CommandParser) -> None:
    templates: dict[str, tuple[str, ...]] = {
        "open_application": (
            "open {application}",
            "launch {application}",
            "start {application}",
            "run {application}",
            "fire up {application}",
        ),
        "close_application": (
            "close {application}",
            "quit {application}",
            "exit {application}",
        ),
        "focus_application": (
            "focus {application}",
            "switch to {application}",
        ),
        "minimize_application": ("minimize {application}",),
        "maximize_application": ("maximize {application}",),
        "restore_application": ("restore {application}",),
    }
    for command_name, phrases in templates.items():
        for phrase in phrases:
            parser.add_pattern(command_name, phrase, _application_only)
