"""Phase 4: the OS layer. The non-Windows tests simulate another OS by
swapping in the fallback backend, which is exactly what get_backend()
returns there."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

import atlas.platform
from atlas.application.voice_loop import VoiceUnavailableError, create_voice
from atlas.config.schema import AtlasConfig
from atlas.platform import PlatformNotSupportedError, _fallback_backend, get_backend
from atlas.platform.keyboard import SPECIAL_KEYS, validate_key

SRC = Path(__file__).resolve().parents[2] / "src" / "atlas"
WINDOWS_ONLY_MODULES = {
    "win32api",
    "win32con",
    "win32gui",
    "win32process",
    "win32com",
    "win32cred",
    "pywintypes",
    "pythoncom",
    "pycaw",
    "winreg",
    "winrt",
}


def test_windows_only_imports_stay_inside_the_win32_backend():
    offenders = []
    for path in SRC.rglob("*.py"):
        if (SRC / "platform" / "win32") in path.parents:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] in WINDOWS_ONLY_MODULES or name.startswith(
                    "atlas.platform.win32"
                ):
                    offenders.append(f"{path.relative_to(SRC)}: {name}")
    assert offenders == []


@pytest.mark.skipif(sys.platform != "win32", reason="Windows backend")
def test_windows_gets_the_full_backend():
    backend = get_backend()
    assert backend.name == "win32"
    assert "windows" in backend.voice_engines
    assert backend.native_transcriber is not None


def test_fallback_backend_fails_clearly_on_every_os_action():
    backend = _fallback_backend()
    calls = [
        lambda: backend.window_manager().list_windows(),
        lambda: backend.monitor_manager().list_monitors(),
        lambda: backend.keyboard_controller().press_key("a"),
        lambda: backend.mouse_controller().click(),
        lambda: backend.system_controller().mute(),
        lambda: backend.application_manager(AtlasConfig(), backend.window_manager()).launch("x"),
        lambda: backend.secret_store.load("x"),
        backend.discover_applications,
    ]
    for call in calls:
        with pytest.raises(PlatformNotSupportedError, match="isn't supported on"):
            call()
    assert backend.voice_engines == {} and backend.native_transcriber is None


def test_atlas_runs_on_an_unsupported_os(monkeypatch):
    """Core, parser and typed commands work; OS actions fail as normal results."""
    from atlas.application import app as app_module

    monkeypatch.setattr(app_module, "get_backend", _fallback_backend)
    monkeypatch.setattr(atlas.platform, "get_backend", _fallback_backend)
    app = app_module.Application()
    app.bootstrap()
    assert app.run_text_command("atlas status").success
    result = app.run_text_command("mute")
    assert not result.success
    assert "isn't supported on" in result.message

    app.config.speech.engine = "windows"
    with pytest.raises(VoiceUnavailableError, match="isn't available"):
        create_voice(app)


def test_every_key_name_maps_to_a_windows_key_code():
    if sys.platform != "win32":
        pytest.skip("Windows key table")
    from atlas.platform.win32.keyboard import key_to_vk

    for name in [*SPECIAL_KEYS, "a", "7", "f1", "f12"]:
        assert key_to_vk(name) > 0


@pytest.mark.parametrize(
    ("key", "expected"),
    [("Control", "ctrl"), ("escape", "esc"), (" ", "space"), ("F12", "f12"), ("q", "q")],
)
def test_validate_key(key, expected):
    assert validate_key(key) == expected


@pytest.mark.parametrize("key", ["f13", "f0", "thisisnotakey", ""])
def test_validate_key_rejects_unknown(key):
    with pytest.raises(ValueError):
        validate_key(key)


def test_app_data_dir_per_os(monkeypatch, tmp_path):
    from atlas.utils import paths

    monkeypatch.setattr(paths.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert paths.get_app_data_dir() == tmp_path / "xdg" / "Atlas"

    monkeypatch.setattr(paths.sys, "platform", "darwin")
    monkeypatch.setattr(paths.Path, "home", lambda: tmp_path)
    assert paths.get_app_data_dir() == tmp_path / "Library" / "Application Support" / "Atlas"
