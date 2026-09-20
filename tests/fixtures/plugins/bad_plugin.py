from atlas.commands.registry import CommandRegistry
from atlas.plugins.base import AtlasPlugin, PluginContext


class _BadPlugin(AtlasPlugin):
    name = "bad_plugin"

    def initialize(self, context: PluginContext) -> None:
        raise RuntimeError("simulated init failure")

    def register_commands(self, registry: CommandRegistry) -> None:
        pass

    def shutdown(self) -> None:
        pass


PLUGIN_CLASS = _BadPlugin
