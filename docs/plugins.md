# Plugin Development

## Interface

```python
from atlas.plugins.base import AtlasPlugin, PluginContext
from atlas.commands.registry import CommandRegistry

class MyPlugin(AtlasPlugin):
    name = "my_plugin"

    def initialize(self, context: PluginContext) -> None:
        ...

    def register_commands(self, registry: CommandRegistry) -> None:
        registry.register(MyCommand)

    def shutdown(self) -> None:
        ...

PLUGIN_CLASS = MyPlugin
```

## Where to put it

- `plugins/my_plugin/__init__.py`, or
- `plugins/my_plugin.py`

Either way, the module must expose `PLUGIN_CLASS` at module scope.

## Discovery and isolation

`atlas.plugins.loader.PluginLoader.discover_and_load` scans a directory,
and for each candidate:

1. imports the module,
2. validates `PLUGIN_CLASS` is an `AtlasPlugin` subclass with a non-empty `name`,
3. instantiates it, calls `initialize()`, then `register_commands()`,
4. records it as loaded in `PluginRegistry`.

**Any exception at any step disables that one plugin** - it is logged with
a reason and recorded in `PluginRegistry` as `DISABLED`; every other
plugin, and ATLAS itself, keeps running (Atlas.md section 44). See
`tests/fixtures/plugins/` for a minimal working plugin and a deliberately
broken one, and `tests/integration/test_plugin_loader.py` for the isolation
test.

## First-party integrations

`src/atlas/integrations/{spotify,browser,filesystem}` are first-party
plugins shipped with ATLAS itself, loaded the same way. They are optional
and core code never imports them directly (Atlas.md section 58) - this is
what lets Spotify's absence, or an auth failure, degrade to "plugin
disabled" instead of an ATLAS-wide failure.
