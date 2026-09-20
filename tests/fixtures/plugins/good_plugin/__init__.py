from atlas.commands.command import Command, CommandContext, CommandResult, ValidationResult
from atlas.commands.registry import CommandRegistry
from atlas.plugins.base import AtlasPlugin, PluginContext


class _PingCommand(Command):
    name = "fixture_ping"

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        return CommandResult.ok("pong")

    def describe(self) -> str:
        return "fixture ping command"


class _GoodPlugin(AtlasPlugin):
    name = "good_plugin"

    def initialize(self, context: PluginContext) -> None:
        pass

    def register_commands(self, registry: CommandRegistry) -> None:
        registry.register(_PingCommand)

    def shutdown(self) -> None:
        pass


PLUGIN_CLASS = _GoodPlugin
