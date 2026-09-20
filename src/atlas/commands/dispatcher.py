"""Validates and executes parsed commands. This is the safety boundary: a
command's exception can never propagate out and kill the process (Atlas.md
section 33, section 56)."""

from __future__ import annotations

from atlas.commands.command import Command, CommandContext, CommandResult
from atlas.logging_setup import get_logger
from atlas.security.permissions import requires_confirmation

logger = get_logger("dispatcher")


class AwaitingConfirmation(Exception):
    def __init__(self, command: Command) -> None:
        self.command = command
        super().__init__(f"Command '{command.name}' requires confirmation")


class CommandDispatcher:
    def __init__(self, *, confirmations_enabled: bool = True) -> None:
        self._confirmations_enabled = confirmations_enabled

    def dispatch(
        self,
        command: Command,
        context: CommandContext,
        *,
        confirmed: bool = False,
    ) -> CommandResult:
        if (
            requires_confirmation(command.name, confirmations_enabled=self._confirmations_enabled)
            and not confirmed
        ):
            raise AwaitingConfirmation(command)

        validation = command.validate()
        if not validation.ok:
            logger.warning("Validation failed for %s: %s", command.name, validation.errors)
            return CommandResult.fail("; ".join(validation.errors) or "Validation failed")

        logger.info("Executing command: %s", command.describe())
        try:
            result = command.execute(context)
        except Exception as exc:  # noqa: BLE001 - intentional: this is the safety boundary
            logger.exception("Command '%s' raised an exception during execution", command.name)
            return CommandResult.fail(f"Command failed: {exc}")

        logger.info("Command '%s' completed: success=%s", command.name, result.success)
        return result
