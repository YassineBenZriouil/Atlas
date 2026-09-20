"""Plugin discovery/loading with isolation (Atlas.md sections 43-44). A
broken plugin must never crash ATLAS - every stage below is caught per
plugin and turned into a disabled-with-reason record."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from atlas.commands.registry import CommandRegistry
from atlas.logging_setup import get_logger
from atlas.plugins.base import AtlasPlugin, PluginContext
from atlas.plugins.registry import PluginRegistry

logger = get_logger("plugins")

_ENTRY_ATTRIBUTE = "PLUGIN_CLASS"


class PluginLoader:
    def __init__(
        self, command_registry: CommandRegistry, plugin_registry: PluginRegistry
    ) -> None:
        self._command_registry = command_registry
        self._plugin_registry = plugin_registry

    def discover(self, plugins_dir: Path) -> list[Path]:
        """A plugin is either `plugins/<name>/__init__.py` or a standalone
        `plugins/<name>.py` exposing a top-level `PLUGIN_CLASS`."""
        if not plugins_dir.exists():
            return []
        candidates: list[Path] = []
        for entry in sorted(plugins_dir.iterdir()):
            if entry.is_dir() and (entry / "__init__.py").exists():
                candidates.append(entry / "__init__.py")
            elif entry.is_file() and entry.suffix == ".py" and entry.name != "__init__.py":
                candidates.append(entry)
        return candidates

    def discover_and_load(self, plugins_dir: Path) -> None:
        for module_path in self.discover(plugins_dir):
            self._load_one(module_path)

    def _load_one(self, module_path: Path) -> None:
        name = module_path.parent.name if module_path.name == "__init__.py" else module_path.stem
        try:
            spec = importlib.util.spec_from_file_location(f"atlas_plugin_{name}", module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load spec for {module_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin_cls = getattr(module, _ENTRY_ATTRIBUTE, None)
            if plugin_cls is None:
                raise ImportError(f"{module_path} does not define `{_ENTRY_ATTRIBUTE}`")
            if not (isinstance(plugin_cls, type) and issubclass(plugin_cls, AtlasPlugin)):
                raise TypeError(
                    f"`{_ENTRY_ATTRIBUTE}` in {module_path} is not an AtlasPlugin subclass"
                )

            plugin: AtlasPlugin = plugin_cls()
            if not plugin.name:
                raise ValueError("Plugin must define a non-empty `name`")

            plugin.initialize(PluginContext())
            plugin.register_commands(self._command_registry)

            self._plugin_registry.mark_loaded(plugin)
            logger.info("Plugin loaded: %s", plugin.name)
        except Exception as exc:  # noqa: BLE001 - plugin isolation boundary
            logger.error("Plugin disabled: %s (reason: %s)", name, exc)
            self._plugin_registry.mark_disabled(name, str(exc))

    def shutdown_all(self) -> None:
        for plugin in self._plugin_registry.loaded_plugins():
            try:
                plugin.shutdown()
            except Exception:  # noqa: BLE001 - shutdown must never abort partway
                logger.exception("Plugin '%s' raised during shutdown", plugin.name)
