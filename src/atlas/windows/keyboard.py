"""Keyboard automation abstraction (Atlas.md section 24), plus the Win32
implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod

import win32api
import win32con

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

_SPECIAL_VK_CODES: dict[str, int] = {
    "enter": win32con.VK_RETURN,
    "esc": win32con.VK_ESCAPE,
    "tab": win32con.VK_TAB,
    "space": win32con.VK_SPACE,
    "ctrl": win32con.VK_CONTROL,
    "alt": win32con.VK_MENU,
    "shift": win32con.VK_SHIFT,
    "win": win32con.VK_LWIN,
    "backspace": win32con.VK_BACK,
    "delete": win32con.VK_DELETE,
    "left": win32con.VK_LEFT,
    "up": win32con.VK_UP,
    "right": win32con.VK_RIGHT,
    "down": win32con.VK_DOWN,
}


def normalize_key(key: str) -> str:
    return KEY_ALIASES.get(key.lower(), key.lower())


def key_to_vk(key: str) -> int:
    normalized = normalize_key(key)
    if normalized == " ":
        normalized = "space"
    if normalized in _SPECIAL_VK_CODES:
        return _SPECIAL_VK_CODES[normalized]
    if len(normalized) == 1 and normalized.isalnum():
        return ord(normalized.upper())
    if normalized.startswith("f") and normalized[1:].isdigit() and 1 <= int(normalized[1:]) <= 12:
        return win32con.VK_F1 + (int(normalized[1:]) - 1)
    raise ValueError(f"Unknown key: {key}")


class KeyboardController(ABC):
    @abstractmethod
    def press_key(self, key: str) -> None: ...

    @abstractmethod
    def press_combo(self, keys: list[str]) -> None: ...


class Win32KeyboardController(KeyboardController):
    def press_key(self, key: str) -> None:
        vk = key_to_vk(key)
        win32api.keybd_event(vk, 0, 0, 0)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

    def press_combo(self, keys: list[str]) -> None:
        vks = [key_to_vk(key) for key in keys]
        for vk in vks:
            win32api.keybd_event(vk, 0, 0, 0)
        for vk in reversed(vks):
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
