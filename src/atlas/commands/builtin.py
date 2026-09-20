"""Placeholder/developer commands (Atlas.md section 16): atlas status/test/help.

These prove the full pipeline - normalization, matching, registry lookup,
validation, execution - works end-to-end without depending on any
Windows-specific integration.
"""

from __future__ import annotations

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


class StatusCommand(Command):
    name = "atlas_status"
    category = CommandCategory.DEVELOPER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        state = context.extra.get("state_name", "unknown")
        return CommandResult.ok(f"ATLAS is running. State: {state}", state=state)

    def describe(self) -> str:
        return "Report current ATLAS state"


class TestCommand(Command):
    name = "atlas_test"
    category = CommandCategory.DEVELOPER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        return CommandResult.ok("Self-test passed: command pipeline is operational.")

    def describe(self) -> str:
        return "Run an internal self-test of the command pipeline"


class HelpCommand(Command):
    name = "atlas_help"
    category = CommandCategory.DEVELOPER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        registry: CommandRegistry | None = context.extra.get("registry")
        if registry is None:
            return CommandResult.ok("No commands registered.")
        names = registry.names()
        return CommandResult.ok("Available commands: " + ", ".join(names), commands=names)

    def describe(self) -> str:
        return "List available commands"


BUILTIN_COMMANDS: tuple[type[Command], ...] = (StatusCommand, TestCommand, HelpCommand)


def register_builtin_commands(registry: CommandRegistry) -> None:
    for command_cls in BUILTIN_COMMANDS:
        if command_cls.name not in registry:
            registry.register(command_cls)


def register_builtin_grammars(parser: CommandParser) -> None:
    parser.add_grammar(Grammar("atlas_status", ("atlas status", "status")))
    parser.add_grammar(Grammar("atlas_test", ("atlas test", "test")))
    parser.add_grammar(Grammar("atlas_help", ("atlas help", "help", "what can you do")))
