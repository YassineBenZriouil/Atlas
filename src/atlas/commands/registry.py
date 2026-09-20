"""Central command registry (Atlas.md section 14). Plugins register here
instead of the parser containing a giant if/elif chain."""

from __future__ import annotations

from atlas.commands.command import Command


class CommandAlreadyRegisteredError(RuntimeError):
    pass


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, type[Command]] = {}

    def register(self, command_cls: type[Command]) -> None:
        name = command_cls.name
        if not name:
            raise ValueError(f"{command_cls.__name__} must define a non-empty `name`")
        if name in self._commands:
            raise CommandAlreadyRegisteredError(f"Command already registered: {name}")
        self._commands[name] = command_cls

    def unregister(self, name: str) -> None:
        self._commands.pop(name, None)

    def get(self, name: str) -> type[Command] | None:
        return self._commands.get(name)

    def names(self) -> list[str]:
        return sorted(self._commands)

    def all(self) -> dict[str, type[Command]]:
        return dict(self._commands)

    def __contains__(self, name: str) -> bool:
        return name in self._commands

    def __len__(self) -> int:
        return len(self._commands)
