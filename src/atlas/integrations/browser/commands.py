"""Browser control via keyboard shortcuts (Atlas.md section 26) - no
browser extension required. Tab/navigation commands act on whichever known
browser window is currently open; if none is open they fail clearly rather
than launching one implicitly ("open brave" is what does that)."""

from __future__ import annotations

import urllib.parse
import webbrowser
from dataclasses import dataclass

from atlas.commands.command import (
    Command,
    CommandCategory,
    CommandContext,
    CommandResult,
    ValidationResult,
)
from atlas.commands.matcher import Grammar
from atlas.commands.parser import CommandParser
from atlas.commands.registry import CommandRegistry
from atlas.windows.windows import WindowHandle, WindowManager

_BROWSER_PROCESS_NAMES = ("brave.exe", "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe")
_DEFAULT_SEARCH_URL = "https://www.google.com/search?q={query}"


def _find_browser_window(window_manager: WindowManager) -> WindowHandle | None:
    for window in window_manager.list_windows():
        if window.process_name.lower() in _BROWSER_PROCESS_NAMES:
            return window
    return None


def _focus_browser(context: CommandContext) -> WindowHandle | CommandResult:
    window_manager: WindowManager = context.extra["window_manager"]
    window = _find_browser_window(window_manager)
    if window is None:
        return CommandResult.fail("No browser is open")
    window_manager.focus_window(window)
    return window


class NewTabCommand(Command):
    name = "browser_new_tab"
    category = CommandCategory.BROWSER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _focus_browser(context)
        if isinstance(window, CommandResult):
            return window
        context.extra["keyboard_controller"].press_combo(["ctrl", "t"])
        return CommandResult.ok("Opened new tab")

    def describe(self) -> str:
        return "Open a new browser tab"


class CloseTabCommand(Command):
    name = "browser_close_tab"
    category = CommandCategory.BROWSER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _focus_browser(context)
        if isinstance(window, CommandResult):
            return window
        context.extra["keyboard_controller"].press_combo(["ctrl", "w"])
        return CommandResult.ok("Closed tab")

    def describe(self) -> str:
        return "Close the current browser tab"


class NextTabCommand(Command):
    name = "browser_next_tab"
    category = CommandCategory.BROWSER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _focus_browser(context)
        if isinstance(window, CommandResult):
            return window
        context.extra["keyboard_controller"].press_combo(["ctrl", "tab"])
        return CommandResult.ok("Switched to next tab")

    def describe(self) -> str:
        return "Switch to the next browser tab"


class PreviousTabCommand(Command):
    name = "browser_previous_tab"
    category = CommandCategory.BROWSER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _focus_browser(context)
        if isinstance(window, CommandResult):
            return window
        context.extra["keyboard_controller"].press_combo(["ctrl", "shift", "tab"])
        return CommandResult.ok("Switched to previous tab")

    def describe(self) -> str:
        return "Switch to the previous browser tab"


class RefreshCommand(Command):
    name = "browser_refresh"
    category = CommandCategory.BROWSER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _focus_browser(context)
        if isinstance(window, CommandResult):
            return window
        context.extra["keyboard_controller"].press_key("f5")
        return CommandResult.ok("Refreshed")

    def describe(self) -> str:
        return "Refresh the current page"


class GoBackCommand(Command):
    name = "browser_back"
    category = CommandCategory.BROWSER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _focus_browser(context)
        if isinstance(window, CommandResult):
            return window
        context.extra["keyboard_controller"].press_combo(["alt", "left"])
        return CommandResult.ok("Went back")

    def describe(self) -> str:
        return "Go back a page"


class GoForwardCommand(Command):
    name = "browser_forward"
    category = CommandCategory.BROWSER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _focus_browser(context)
        if isinstance(window, CommandResult):
            return window
        context.extra["keyboard_controller"].press_combo(["alt", "right"])
        return CommandResult.ok("Went forward")

    def describe(self) -> str:
        return "Go forward a page"


class FocusAddressBarCommand(Command):
    name = "browser_focus_address_bar"
    category = CommandCategory.BROWSER

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _focus_browser(context)
        if isinstance(window, CommandResult):
            return window
        context.extra["keyboard_controller"].press_combo(["ctrl", "l"])
        return CommandResult.ok("Focused address bar")

    def describe(self) -> str:
        return "Focus the address bar"


@dataclass
class BrowserSearchCommand(Command):
    """Types into the currently-focused browser's address bar/omnibox,
    which searches using whatever engine the browser itself is configured
    with - distinct from WebSearchCommand, which opens a fixed search URL
    directly and doesn't need a browser window open yet."""

    query: str
    name = "browser_search"
    category = CommandCategory.BROWSER

    def validate(self) -> ValidationResult:
        if not self.query.strip():
            return ValidationResult.failure("No search query given")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        window = _focus_browser(context)
        if isinstance(window, CommandResult):
            return window
        keyboard = context.extra["keyboard_controller"]
        keyboard.press_combo(["ctrl", "l"])
        for char in self.query:
            keyboard.press_key(char)
        keyboard.press_key("enter")
        return CommandResult.ok(f"Searching for {self.query}")

    def describe(self) -> str:
        return f"Search for {self.query}"


@dataclass
class WebSearchCommand(Command):
    query: str
    name = "web_search"
    category = CommandCategory.BROWSER

    def validate(self) -> ValidationResult:
        if not self.query.strip():
            return ValidationResult.failure("No search query given")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        url = _DEFAULT_SEARCH_URL.format(query=urllib.parse.quote_plus(self.query))
        webbrowser.open(url)
        return CommandResult.ok(f"Searching the web for {self.query}")

    def describe(self) -> str:
        return f"Search the web for {self.query}"


_COMMANDS: tuple[type[Command], ...] = (
    NewTabCommand,
    CloseTabCommand,
    NextTabCommand,
    PreviousTabCommand,
    RefreshCommand,
    GoBackCommand,
    GoForwardCommand,
    FocusAddressBarCommand,
    BrowserSearchCommand,
    WebSearchCommand,
)


def register(registry: CommandRegistry) -> None:
    for command_cls in _COMMANDS:
        if command_cls.name not in registry:
            registry.register(command_cls)


def _query_builder(groups: dict[str, str]) -> dict[str, str]:
    return {"query": groups["query"].strip()}


def register_grammars(parser: CommandParser) -> None:
    parser.add_grammar(Grammar("browser_new_tab", ("new tab", "open a new tab")))
    parser.add_grammar(Grammar("browser_close_tab", ("close tab",)))
    parser.add_grammar(Grammar("browser_next_tab", ("next tab",)))
    parser.add_grammar(Grammar("browser_previous_tab", ("previous tab",)))
    parser.add_grammar(Grammar("browser_refresh", ("refresh",)))
    parser.add_grammar(Grammar("browser_back", ("go back",)))
    parser.add_grammar(Grammar("browser_forward", ("go forward",)))
    parser.add_grammar(
        Grammar("browser_focus_address_bar", ("focus address bar", "focus the address bar"))
    )

    # Most-specific templates first: "search {query}" would otherwise
    # swallow "search the web for ..." whole.
    for phrase in ("search the web for {query}", "search the web for {query} online"):
        parser.add_pattern("web_search", phrase, _query_builder)
    parser.add_pattern("browser_search", "search {query}", _query_builder)
