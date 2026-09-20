from pathlib import Path

from atlas.commands.registry import CommandRegistry
from atlas.plugins.loader import PluginLoader
from atlas.plugins.registry import PluginRegistry, PluginStatus

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "plugins"


def test_good_plugin_loads_and_registers_command():
    command_registry = CommandRegistry()
    plugin_registry = PluginRegistry()
    loader = PluginLoader(command_registry, plugin_registry)

    loader.discover_and_load(FIXTURES_DIR)

    assert "fixture_ping" in command_registry
    record = plugin_registry.get("good_plugin")
    assert record is not None
    assert record.status is PluginStatus.LOADED


def test_bad_plugin_is_disabled_without_crashing():
    command_registry = CommandRegistry()
    plugin_registry = PluginRegistry()
    loader = PluginLoader(command_registry, plugin_registry)

    loader.discover_and_load(FIXTURES_DIR)

    record = plugin_registry.get("bad_plugin")
    assert record is not None
    assert record.status is PluginStatus.DISABLED
    assert "simulated init failure" in record.reason


def test_missing_plugins_dir_is_not_an_error(tmp_path):
    command_registry = CommandRegistry()
    plugin_registry = PluginRegistry()
    loader = PluginLoader(command_registry, plugin_registry)

    loader.discover_and_load(tmp_path / "does-not-exist")

    assert plugin_registry.all() == []
