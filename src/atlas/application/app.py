"""Top-level orchestrator wiring config, logging, commands, and plugins
together (Atlas.md section 0 / section 85: "prove the architecture works")."""

from __future__ import annotations

from atlas.application.lifecycle import CrashGuard, Lifecycle
from atlas.application.state import AtlasState, StateMachine
from atlas.commands.builtin import register_builtin_commands, register_builtin_grammars
from atlas.commands.command import CommandContext, CommandResult
from atlas.commands.dispatcher import AwaitingConfirmation, CommandDispatcher
from atlas.commands.parser import CommandParser
from atlas.commands.registry import CommandRegistry
from atlas.config.loader import load_config
from atlas.config.schema import AtlasConfig
from atlas.logging_setup import configure_logging, get_logger
from atlas.plugins.loader import PluginLoader
from atlas.plugins.registry import PluginRegistry
from atlas.utils.paths import get_config_path, get_log_dir, get_plugins_dir

logger = get_logger("application")


class Application:
    """Owns every subsystem's lifetime. `bootstrap()` must run before any
    other method is used."""

    def __init__(self) -> None:
        self.config: AtlasConfig | None = None
        self.state_machine = StateMachine()
        self.command_registry = CommandRegistry()
        self.plugin_registry = PluginRegistry()
        self.lifecycle = Lifecycle()
        self.crash_guard = CrashGuard()
        self.parser: CommandParser | None = None
        self.dispatcher: CommandDispatcher | None = None
        self.plugin_loader: PluginLoader | None = None

    def bootstrap(self) -> None:
        self.config = load_config(get_config_path())
        configure_logging(
            get_log_dir(),
            level=self.config.logging.level,
            max_bytes=self.config.logging.max_bytes,
            backup_count=self.config.logging.backup_count,
        )
        logger.info("ATLAS bootstrap starting")

        register_builtin_commands(self.command_registry)
        self.parser = CommandParser(self.command_registry)
        register_builtin_grammars(self.parser)
        self.dispatcher = CommandDispatcher(
            confirmations_enabled=self.config.commands.require_confirmation
        )

        self.plugin_loader = PluginLoader(self.command_registry, self.plugin_registry)
        self.plugin_loader.discover_and_load(get_plugins_dir())

        self.state_machine.on_change(
            lambda prev, cur: logger.debug("Application state: %s -> %s", prev.name, cur.name)
        )
        logger.info("ATLAS bootstrap complete")

    def run_text_command(self, text: str) -> CommandResult:
        """Drives one full pass of the pipeline in Atlas.md section 6, for a
        single already-transcribed line of text. Used by the developer
        console and by tests; Phase 2 wires real speech input into this same
        entry point."""
        if self.parser is None or self.dispatcher is None or self.config is None:
            raise RuntimeError("Application.bootstrap() must be called first")

        try:
            self.state_machine.transition(AtlasState.WAKE_DETECTED)
            self.state_machine.transition(AtlasState.LISTENING)
            self.state_machine.transition(AtlasState.RECOGNIZING)
            self.state_machine.transition(AtlasState.PARSING)

            parse_result = self.parser.parse(text)
            if not parse_result.ok:
                self.state_machine.fail(parse_result.error or "parse failed")
                self.state_machine.recover()
                return CommandResult.fail(
                    parse_result.error or "I didn't understand that command."
                )

            self.state_machine.transition(AtlasState.VALIDATING)
            context = CommandContext(
                app_state=self.state_machine,
                config=self.config,
                extra={
                    "registry": self.command_registry,
                    "state_name": self.state_machine.state.name,
                },
            )
            self.state_machine.transition(AtlasState.EXECUTING)
            assert parse_result.command is not None
            result = self.dispatcher.dispatch(parse_result.command, context)

            self.state_machine.transition(AtlasState.FEEDBACK)
            self.state_machine.transition(AtlasState.SLEEPING)
            return result
        except AwaitingConfirmation:
            self.state_machine.fail("awaiting confirmation")
            self.state_machine.recover()
            raise
        except Exception as exc:  # noqa: BLE001 - Application is the outer safety boundary
            logger.exception("Unexpected failure while running command")
            self.state_machine.fail(str(exc))
            self.state_machine.recover()
            return CommandResult.fail(f"Internal error: {exc}")

    def shutdown(self) -> None:
        logger.info("ATLAS shutting down")
        if self.plugin_loader is not None:
            self.plugin_loader.shutdown_all()
        self.lifecycle.shutdown()
