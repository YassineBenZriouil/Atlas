"""Keyboard automation interface (Atlas.md section 24) and the key names
ATLAS understands. Backends map these names to their own key codes."""

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
    " ": "space",
    "windows": "win",
    "win": "win",
    "alt": "alt",
    "shift": "shift",
}

SPECIAL_KEYS = frozenset(
    {
        "enter",
        "esc",
        "tab",
        "space",
        "ctrl",
        "alt",
        "shift",
        "win",
        "backspace",
        "delete",
        "left",
        "up",
        "right",
        "down",
    }
)


def normalize_key(key: str) -> str:
    return KEY_ALIASES.get(key.lower(), key.lower())


def validate_key(key: str) -> str:
    """The canonical key name: a special key, one letter/digit, or f1-f12.
    Raises ValueError for anything else."""
    name = normalize_key(key)
    if name in SPECIAL_KEYS or (len(name) == 1 and name.isalnum()):
        return name
    if name.startswith("f") and name[1:].isdigit() and 1 <= int(name[1:]) <= 12:
        return name
    raise ValueError(f"Unknown key: {key}")


class KeyboardController(ABC):
    @abstractmethod
    def press_key(self, key: str) -> None: ...

    @abstractmethod
    def press_combo(self, keys: list[str]) -> None: ...
