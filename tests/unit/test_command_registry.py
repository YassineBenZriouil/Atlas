import pytest

from atlas.commands.command import Command, CommandResult, ValidationResult
from atlas.commands.registry import CommandAlreadyRegisteredError, CommandRegistry


class DummyCommand(Command):
    name = "dummy"

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context) -> CommandResult:
        return CommandResult.ok("done")

    def describe(self) -> str:
        return "dummy"


def test_register_and_get():
    registry = CommandRegistry()
    registry.register(DummyCommand)
    assert registry.get("dummy") is DummyCommand
    assert "dummy" in registry
    assert len(registry) == 1


def test_duplicate_registration_raises():
    registry = CommandRegistry()
    registry.register(DummyCommand)
    with pytest.raises(CommandAlreadyRegisteredError):
        registry.register(DummyCommand)


def test_unnamed_command_rejected():
    class Unnamed(Command):
        def validate(self) -> ValidationResult:
            return ValidationResult.success()

        def execute(self, context) -> CommandResult:
            return CommandResult.ok()

        def describe(self) -> str:
            return ""

    registry = CommandRegistry()
    with pytest.raises(ValueError):
        registry.register(Unnamed)


def test_names_sorted():
    registry = CommandRegistry()
    registry.register(DummyCommand)
    assert registry.names() == ["dummy"]


def test_unregister():
    registry = CommandRegistry()
    registry.register(DummyCommand)
    registry.unregister("dummy")
    assert registry.get("dummy") is None
