"""Real filesystem/registry lookups but never launches anything - safe to
run in every test session."""

from atlas.config.defaults import default_config
from atlas.windows.applications import Win32ApplicationManager
from atlas.windows.windows import Win32WindowManager


def make_manager() -> Win32ApplicationManager:
    return Win32ApplicationManager(default_config(), Win32WindowManager())


def test_locate_notepad_finds_system_binary():
    path = make_manager().locate("notepad")
    assert path is not None
    assert path.lower().endswith("notepad.exe")


def test_locate_unknown_alias_returns_none():
    assert make_manager().locate("definitely-not-a-real-application-xyz") is None


def test_resolve_alias_from_config():
    info = make_manager().resolve_alias("vs code")
    assert info is not None
    assert info.alias == "vscode"


def test_resolve_unknown_alias_returns_none():
    assert make_manager().resolve_alias("nonexistent") is None


def test_is_running_false_for_unlaunched_app():
    assert make_manager().is_running("definitely-not-a-real-application-xyz") is False
