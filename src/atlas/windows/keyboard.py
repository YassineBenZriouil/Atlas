"""Keyboard automation abstraction (Atlas.md section 24)."""

from __future__ import annotations

from abc import ABC, abstractmethod

KEY_ALIASES: dict[str, str] = {
    "control": "ctrl",
    "ctrl": "ctrl",
    "escape": "esc",
    "esc": "esc",
    "enter": "enter",
    "return": "enter",
    "tab": "tab",
    "space": "space",
    "windows": "win",
    "win": "win",
    "alt": "alt",
    "shift": "shift",
}


def normalize_key(key: str) -> str:
    return KEY_ALIASES.get(key.lower(), key.lower())


class KeyboardController(ABC):
    @abstractmethod
    def press_key(self, key: str) -> None: ...

    @abstractmethod
    def press_combo(self, keys: list[str]) -> None: ...
