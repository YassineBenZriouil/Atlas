"""The command interface every ATLAS command must implement (Atlas.md section 13)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class CommandCategory(Enum):
    APPLICATION = auto()
    WINDOW = auto()
    MONITOR = auto()
    MEDIA = auto()
    AUDIO = auto()
    FILESYSTEM = auto()
    BROWSER = auto()
    KEYBOARD = auto()
    MOUSE = auto()
    SYSTEM = auto()
    SPOTIFY = auto()
    DEVELOPER = auto()
    CUSTOM = auto()


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...] = ()

    @staticmethod
    def success() -> ValidationResult:
        return ValidationResult(ok=True)

    @staticmethod
    def failure(*errors: str) -> ValidationResult:
        return ValidationResult(ok=False, errors=errors)


@dataclass(frozen=True)
class CommandResult:
    success: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def ok(message: str = "", **data: Any) -> CommandResult:
        return CommandResult(success=True, message=message, data=data)

    @staticmethod
    def fail(message: str, **data: Any) -> CommandResult:
        return CommandResult(success=False, message=message, data=data)


@dataclass
class CommandContext:
    """Runtime services available to a command's execute(). Grows in Phase 2
    as WindowManager/ApplicationManager/etc. become concrete."""

    app_state: Any = None
    config: Any = None
    extra: dict[str, Any] = field(default_factory=dict)


class Command(ABC):
    name: str = ""
    category: CommandCategory = CommandCategory.CUSTOM

    @abstractmethod
    def validate(self) -> ValidationResult: ...

    @abstractmethod
    def execute(self, context: CommandContext) -> CommandResult: ...

    @abstractmethod
    def describe(self) -> str: ...
