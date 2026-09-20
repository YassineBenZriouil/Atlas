"""Opens/closes real windows and briefly touches system volume - opt in with
ATLAS_TEST_DESKTOP=1 so a normal `pytest` run never disrupts the desktop."""

import os
import time

import pytest

from atlas.config.defaults import default_config
from atlas.windows.applications import Win32ApplicationManager
from atlas.windows.keyboard import Win32KeyboardController
from atlas.windows.system import Win32SystemController
from atlas.windows.windows import Win32WindowManager

requires_desktop = pytest.mark.skipif(
    os.environ.get("ATLAS_TEST_DESKTOP") != "1",
    reason="Opens/moves real windows and touches system volume; "
    "set ATLAS_TEST_DESKTOP=1 to run.",
)


@requires_desktop
def test_notepad_lifecycle():
    window_manager = Win32WindowManager()
    app_manager = Win32ApplicationManager(default_config(), window_manager)

    assert not app_manager.is_running("notepad")
    app_manager.launch("notepad")
    try:
        window = None
        for _ in range(40):
            window = window_manager.find_window("notepad")
            if window:
                break
            time.sleep(0.25)
        assert window is not None

        window_manager.focus_window(window)
        window_manager.maximize_window(window)
        window_manager.restore_window(window)
        window_manager.minimize_window(window)
        window_manager.restore_window(window)
        window_manager.resize_window(window, 640, 480)
    finally:
        app_manager.terminate("notepad")
        time.sleep(0.5)
    assert not app_manager.is_running("notepad")


@requires_desktop
def test_keyboard_combo_does_not_raise():
    keyboard = Win32KeyboardController()
    keyboard.press_key("a")
    keyboard.press_combo(["ctrl", "a"])


@requires_desktop
def test_volume_and_screenshot(tmp_path):
    system = Win32SystemController()
    system.unmute()
    system.set_volume(30)
    system.volume_up(5)
    system.volume_down(5)

    destination = tmp_path / "shot.png"
    result = system.take_screenshot(destination)
    assert result.exists()
    assert result.stat().st_size > 0
