from tests.fixtures.fakes import FakeKeyboardController, FakeWindowManager

from atlas.commands.command import CommandContext
from atlas.integrations.browser.commands import (
    CloseTabCommand,
    NewTabCommand,
    RefreshCommand,
    WebSearchCommand,
)


def make_context(window_manager: FakeWindowManager, keyboard: FakeKeyboardController):
    return CommandContext(
        extra={"window_manager": window_manager, "keyboard_controller": keyboard}
    )


def test_new_tab_fails_when_no_browser_open():
    result = NewTabCommand().execute(make_context(FakeWindowManager(), FakeKeyboardController()))
    assert not result.success
    assert "No browser" in result.message


def test_new_tab_sends_ctrl_t_when_browser_open():
    window_manager = FakeWindowManager()
    window_manager.add_window("Brave", "brave.exe")
    keyboard = FakeKeyboardController()

    result = NewTabCommand().execute(make_context(window_manager, keyboard))

    assert result.success
    assert ["ctrl", "t"] in keyboard.combos


def test_close_tab_sends_ctrl_w():
    window_manager = FakeWindowManager()
    window_manager.add_window("Brave", "brave.exe")
    keyboard = FakeKeyboardController()

    CloseTabCommand().execute(make_context(window_manager, keyboard))

    assert ["ctrl", "w"] in keyboard.combos


def test_refresh_sends_f5():
    window_manager = FakeWindowManager()
    window_manager.add_window("Brave", "brave.exe")
    keyboard = FakeKeyboardController()

    RefreshCommand().execute(make_context(window_manager, keyboard))

    assert "f5" in keyboard.pressed


def test_web_search_opens_url_without_requiring_a_browser_window(monkeypatch):
    opened: list[str] = []
    monkeypatch.setattr(
        "atlas.integrations.browser.commands.webbrowser.open", lambda url: opened.append(url)
    )

    result = WebSearchCommand(query="jay z").execute(
        make_context(FakeWindowManager(), FakeKeyboardController())
    )

    assert result.success
    assert len(opened) == 1
    assert "jay" in opened[0]


def test_web_search_rejects_empty_query():
    assert not WebSearchCommand(query="  ").validate().ok
