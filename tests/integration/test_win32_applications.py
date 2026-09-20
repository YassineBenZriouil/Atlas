"""Real filesystem/registry lookups but never launches anything - safe to
run in every test session."""

from atlas.commands.application_commands import _display_name
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


def test_resolve_alias_fuzzy_matches_asr_misrecognition():
    """Real-world case: Vosk transcribed "vs code" as "vs cold" - a
    single-character substitution should still resolve (Atlas.md section
    63 explicitly permits fuzzy matching for application aliases)."""
    info = make_manager().resolve_alias("vs cold")
    assert info is not None
    assert info.alias == "vscode"


def test_resolve_alias_fuzzy_matches_doubled_letter():
    info = make_manager().resolve_alias("spotifyy")
    assert info is not None
    assert info.alias == "spotify"


def test_resolve_alias_fuzzy_does_not_match_command_verbs():
    """"close" must never resolve to "code" via fuzzy matching - that
    would be a command verb accidentally being treated as an app name."""
    assert make_manager().resolve_alias("close") is None


def test_resolve_alias_fuzzy_does_not_match_unrelated_text():
    assert make_manager().resolve_alias("definitely-not-a-real-application-xyz") is None


def test_display_name_echoes_resolved_alias_not_misheard_text():
    """A response should say what ATLAS actually did ("vscode"), not
    parrot back a misheard "vs cold"."""
    assert _display_name(make_manager(), "vs cold") == "vscode"


def test_display_name_falls_back_to_raw_text_when_unresolved():
    assert _display_name(make_manager(), "definitely-unresolvable") == "definitely-unresolvable"


def test_is_running_false_for_unlaunched_app():
    assert make_manager().is_running("definitely-not-a-real-application-xyz") is False
