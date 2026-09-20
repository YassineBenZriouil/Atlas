"""Confirmation policy for dangerous commands (Atlas.md sections 40-41).

This module NEVER executes anything. It only decides whether a command's
category requires spoken/typed confirmation before the dispatcher may call
`Command.execute`.
"""

from __future__ import annotations

DANGEROUS_COMMAND_NAMES: frozenset[str] = frozenset(
    {
        "shutdown_computer",
        "restart_computer",
        "logout",
        "delete_file",
        "format_drive",
        "factory_reset",
        "terminate_process",
    }
)


def is_dangerous(command_name: str) -> bool:
    return command_name in DANGEROUS_COMMAND_NAMES


def requires_confirmation(command_name: str, *, confirmations_enabled: bool) -> bool:
    """Whether the dispatcher must obtain an explicit "confirm" before executing.

    Confirmation may be disabled globally in configuration, but a dangerous
    command MUST still require confirmation by default - this is a safety
    invariant, not a convenience toggle.
    """
    if not is_dangerous(command_name):
        return False
    return confirmations_enabled
