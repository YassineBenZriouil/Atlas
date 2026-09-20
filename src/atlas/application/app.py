"""Top-level orchestrator wiring config, logging, commands, and plugins
together (Atlas.md section 0 / section 85: "prove the architecture works")."""

from __future__ import annotations

from atlas.application.lifecycle import CrashGuard, Lifecycle
from atlas.application.state import AtlasState, StateMachine
from atlas.commands import application_commands, keyboard_commands, system_commands, window_commands
from atlas.commands.builtin import register_builtin_commands, register_builtin_grammars
from atlas.commands.command import Command, CommandContext, CommandResult
from atlas.commands.dispatcher import AwaitingConfirmation, CommandDispatcher
from atlas.commands.parser import CommandParser, NeedsClarification
from atlas.commands.registry import CommandRegistry
from atlas.config.loader import load_config
from atlas.config.schema import AtlasConfig
from atlas.integrations.browser import commands as browser_commands
from atlas.logging_setup import configure_logging, get_logger
from atlas.plugins.loader import PluginLoader
from atlas.plugins.registry import PluginRegistry
from atlas.utils.paths import get_config_path, get_log_dir, get_plugins_dir
from atlas.utils.strings import normalize
from atlas.windows.applications import ApplicationManager, Win32ApplicationManager
from atlas.windows.keyboard import KeyboardController, Win32KeyboardController
from atlas.windows.monitors import MonitorManager, Win32MonitorManager
from atlas.windows.mouse import MouseController, Win32MouseController
from atlas.windows.system import SystemController, Win32SystemController
from atlas.windows.windows import Win32WindowManager, WindowManager

logger = get_logger("application")

_CONFIRMATION_WORDS = ("confirm", "yes", "confirmed", "do it")


class Application:
    """Owns every subsystem's lifetime. `bootstrap()` must run before any
    other method is used.

    Windows-layer managers default to the real Win32-backed
    implementations but can be injected (e.g. in tests, to avoid actually
    shutting down the machine when exercising the confirmation flow)."""

    def __init__(
        self,
        *,
        window_manager: WindowManager | None = None,
        monitor_manager: MonitorManager | None = None,
        keyboard_controller: KeyboardController | None = None,
        mouse_controller: MouseController | None = None,
        system_controller: SystemController | None = None,
        application_manager: ApplicationManager | None = None,
    ) -> None:
        self.config: AtlasConfig | None = None
        self.state_machine = StateMachine()
        self.command_registry = CommandRegistry()
        self.plugin_registry = PluginRegistry()
        self.lifecycle = Lifecycle()
        self.crash_guard = CrashGuard()
        self.parser: CommandParser | None = None
        self.dispatcher: CommandDispatcher | None = None
        self.plugin_loader: PluginLoader | None = None

        self.window_manager: WindowManager = window_manager or Win32WindowManager()
        self.monitor_manager: MonitorManager = monitor_manager or Win32MonitorManager()
        self.keyboard_controller: KeyboardController = (
            keyboard_controller or Win32KeyboardController()
        )
        self.mouse_controller: MouseController = mouse_controller or Win32MouseController()
        self.system_controller: SystemController = system_controller or Win32SystemController()
        self._injected_application_manager = application_manager
        self.application_manager: ApplicationManager | None = application_manager

        self._pending_clarification: NeedsClarification | None = None
        self._pending_confirmation: tuple[Command, CommandContext] | None = None

    def bootstrap(self) -> None:
        self.config = load_config(get_config_path())
        configure_logging(
            get_log_dir(),
            level=self.config.logging.level,
            max_bytes=self.config.logging.max_bytes,
            backup_count=self.config.logging.backup_count,
        )
        logger.info("ATLAS bootstrap starting")

        self.application_manager = self._injected_application_manager or Win32ApplicationManager(
            self.config, self.window_manager
        )

        register_builtin_commands(self.command_registry)
        application_commands.register(self.command_registry)
        window_commands.register(self.command_registry)
        system_commands.register(self.command_registry)
        browser_commands.register(self.command_registry)
        keyboard_commands.register(self.command_registry)

        self.parser = CommandParser(self.command_registry)
        register_builtin_grammars(self.parser)
        application_commands.register_grammars(self.parser)
        window_commands.register_grammars(self.parser)
        system_commands.register_grammars(self.parser)
        browser_commands.register_grammars(self.parser)
        keyboard_commands.register_grammars(self.parser)

        self.dispatcher = CommandDispatcher(
            confirmations_enabled=self.config.commands.require_confirmation
        )

        self.plugin_loader = PluginLoader(self.command_registry, self.plugin_registry)
        self.plugin_loader.discover_and_load(get_plugins_dir())

        self.state_machine.on_change(
            lambda prev, cur: logger.debug("Application state: %s -> %s", prev.name, cur.name)
        )
        logger.info("ATLAS bootstrap complete")

    def _build_context(self) -> CommandContext:
        assert self.config is not None
        assert self.application_manager is not None
        return CommandContext(
            app_state=self.state_machine,
            config=self.config,
            extra={
                "registry": self.command_registry,
                "state_name": self.state_machine.state.name,
                "window_manager": self.window_manager,
                "monitor_manager": self.monitor_manager,
                "application_manager": self.application_manager,
                "keyboard_controller": self.keyboard_controller,
                "mouse_controller": self.mouse_controller,
                "system_controller": self.system_controller,
            },
        )

    def _advance_to_sleeping(self) -> None:
        """Completes the PARSING -> ... -> SLEEPING sequence for outcomes
        that never reach a real Command (a clarification prompt, a
        cancellation) - the state machine's transition table has no
        shortcut, so this still passes through VALIDATING/EXECUTING."""
        self.state_machine.transition(AtlasState.VALIDATING)
        self.state_machine.transition(AtlasState.EXECUTING)
        self.state_machine.transition(AtlasState.FEEDBACK)
        self.state_machine.transition(AtlasState.SLEEPING)

    def _run_command(self, command: Command) -> CommandResult:
        assert self.dispatcher is not None
        self.state_machine.transition(AtlasState.VALIDATING)
        context = self._build_context()
        self.state_machine.transition(AtlasState.EXECUTING)
        try:
            result = self.dispatcher.dispatch(command, context)
        except AwaitingConfirmation:
            self._pending_confirmation = (command, context)
            self.state_machine.transition(AtlasState.FEEDBACK)
            self.state_machine.transition(AtlasState.SLEEPING)
            return CommandResult.fail(
                f"{command.describe()}. Say 'confirm' to proceed.",
                awaiting_confirmation=True,
            )
        self.state_machine.transition(AtlasState.FEEDBACK)
        self.state_machine.transition(AtlasState.SLEEPING)
        return result

    def run_text_command(self, text: str) -> CommandResult:
        """Drives one full pass of the pipeline in Atlas.md section 6, for a
        single already-transcribed line of text. Used by the developer
        console, the tray, and tests; Phase 2 speech input feeds this same
        entry point once transcribed."""
        if self.parser is None or self.dispatcher is None or self.config is None:
            raise RuntimeError("Application.bootstrap() must be called first")

        try:
            self.state_machine.transition(AtlasState.WAKE_DETECTED)
            self.state_machine.transition(AtlasState.LISTENING)
            self.state_machine.transition(AtlasState.RECOGNIZING)
            self.state_machine.transition(AtlasState.PARSING)

            if self._pending_confirmation is not None:
                command, context = self._pending_confirmation
                self._pending_confirmation = None
                if normalize(text) in _CONFIRMATION_WORDS:
                    self.state_machine.transition(AtlasState.VALIDATING)
                    self.state_machine.transition(AtlasState.EXECUTING)
                    result = self.dispatcher.dispatch(command, context, confirmed=True)
                    self.state_machine.transition(AtlasState.FEEDBACK)
                    self.state_machine.transition(AtlasState.SLEEPING)
                    return result
                self._advance_to_sleeping()
                return CommandResult.fail("Cancelled.")

            if self._pending_clarification is not None:
                clarification = self._pending_clarification
                self._pending_clarification = None
                resolved = clarification.resolve(normalize(text))
                if resolved is None:
                    self._advance_to_sleeping()
                    return CommandResult.fail("Still didn't catch that; command cancelled.")
                return self._run_command(resolved)

            parse_result = self.parser.parse(text)

            if parse_result.needs_clarification:
                assert parse_result.clarification is not None
                self._pending_clarification = parse_result.clarification
                self._advance_to_sleeping()
                return CommandResult.ok(parse_result.clarification.prompt)

            if not parse_result.ok:
                self.state_machine.fail(parse_result.error or "parse failed")
                self.state_machine.recover()
                return CommandResult.fail(
                    parse_result.error or "I didn't understand that command."
                )

            assert parse_result.command is not None
            return self._run_command(parse_result.command)
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
