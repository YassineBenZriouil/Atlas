"""Win32 KeyboardController (Atlas.md section 24): key names -> virtual-key codes."""

from __future__ import annotations

import win32api
import win32con

from atlas.platform.keyboard import KeyboardController, validate_key

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


def key_to_vk(key: str) -> int:
    name = validate_key(key)
    if name in _SPECIAL_VK_CODES:
        return _SPECIAL_VK_CODES[name]
    if len(name) == 1:
        return ord(name.upper())
    return win32con.VK_F1 + (int(name[1:]) - 1)


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
