"""Real filesystem/registry lookups but never launches anything - safe to
run in every test session."""

from unittest.mock import patch

from atlas.commands.application_commands import _display_name
from atlas.config.defaults import default_config
from atlas.config.schema import ApplicationEntry
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


def test_resolve_alias_prefix_matches_disc_for_discord():
    """The exact scenario the user asked for: "disc" is well below the
    ratio-based fuzzy cutoff purely because it's short, but it's an
    unambiguous prefix of the configured "discord" alias (Atlas.md
    section 63 permits this)."""
    info = make_manager().resolve_alias("disc")
    assert info is not None
    assert info.alias == "discord"


def test_resolve_alias_prefix_matches_spot_for_spotify():
    info = make_manager().resolve_alias("spot")
    assert info is not None
    assert info.alias == "spotify"


def test_resolve_alias_prefix_matches_set_for_settings():
    info = make_manager().resolve_alias("set")
    assert info is not None
    assert info.alias == "settings"


def test_resolve_alias_prefix_requires_minimum_length():
    """Below the minimum length a prefix match would be far too
    trigger-happy - nearly everything shares a 1-2 character prefix with
    something. Atlas.md section 63 forbids fuzzy matching that
    effectively becomes guessing."""
    assert make_manager().resolve_alias("s") is None
    assert make_manager().resolve_alias("se") is None


def test_resolve_alias_prefix_refuses_when_ambiguous():
    config = default_config()
    config.applications["settlement_app"] = ApplicationEntry(executable="", aliases=["settlement"])
    manager = Win32ApplicationManager(config, Win32WindowManager())

    # "sett" is now a prefix of both "settings" and "settlement" - ATLAS
    # must refuse rather than guess which one was meant.
    assert manager.resolve_alias("sett") is None


def test_locate_uwp_target_is_returned_as_is():
    config = default_config()
    config.applications["notepad"].executable = "uwp:Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"
    manager = Win32ApplicationManager(config, Win32WindowManager())

    assert manager.locate("notepad") == "uwp:Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"


def test_launch_uwp_target_uses_shell_apps_folder():
    config = default_config()
    config.applications["notepad"].executable = "uwp:Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"
    manager = Win32ApplicationManager(config, Win32WindowManager())

    with patch("atlas.windows.applications.subprocess.Popen") as mock_popen:
        manager.launch("notepad")

    mock_popen.assert_called_once_with(
        ["explorer.exe", "shell:AppsFolder\\Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"],
        shell=False,
    )
