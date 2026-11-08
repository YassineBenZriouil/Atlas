from __future__ import annotations

import asyncio
import os
import sys
import time

import pytest

from atlas.application.app import Application
from atlas.application.voice_loop import VoiceUnavailableError, create_voice
from atlas.config.loader import config_from_dict
from atlas.config.schema import AtlasConfig

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows speech only")


def app_with_engine(engine: str) -> Application:
    app = Application()
    app.config = AtlasConfig()
    app.config.speech.engine = engine
    return app


@windows_only
def test_default_engine_on_windows_is_windows():
    assert AtlasConfig().speech.engine == "windows"


@windows_only
def test_v1_config_migrates_vosk_engine_to_windows():
    config = config_from_dict({"config_version": 1, "speech": {"engine": "vosk"}})
    assert config.speech.engine == "windows"
    assert config.config_version == 2
    # A v2 config that explicitly chose vosk keeps it.
    assert config_from_dict({"config_version": 2, "speech": {"engine": "vosk"}}).speech.engine == (
        "vosk"
    )


@windows_only
def test_create_voice_picks_windows_loop():
    from atlas.platform.win32.voice import WindowsVoiceLoop

    assert isinstance(create_voice(app_with_engine("windows")), WindowsVoiceLoop)


def test_create_voice_rejects_unknown_engine():
    with pytest.raises(VoiceUnavailableError):
        create_voice(app_with_engine("telepathy"))


def test_vosk_engine_without_model_is_unavailable(monkeypatch):
    monkeypatch.setattr("atlas.application.voice_loop.find_default_model", lambda path: None)
    with pytest.raises(VoiceUnavailableError, match="Vosk"):
        create_voice(app_with_engine("vosk"))


class _Outcome:
    def __init__(self, success, message):
        self.success, self.message = success, message


class _FakeApp:
    def __init__(self):
        self.commands = []

    def run_text_command(self, text):
        self.commands.append(text)
        return _Outcome(True, f"ran {text}")


class _FixedTranscriber:
    name = "cloud"

    def __init__(self, text):
        self.text = text

    def transcribe(self, pcm, sample_rate):
        return self.text


def _act(text, pcm, fallback=None):
    from atlas.platform.win32.voice import WindowsVoiceLoop
    from atlas.speech.transcriber import TranscriberChain

    chain = TranscriberChain([] if fallback is None else [_FixedTranscriber(fallback)])
    app, events = _FakeApp(), []
    loop = WindowsVoiceLoop(app, transcribers=chain, on_event=lambda k, m: events.append((k, m)))
    asyncio.run(loop._act(text, "windows", pcm))
    return app, events


AUDIO = b"\x01\x00" * 1600


@windows_only
def test_grammar_match_runs_without_touching_fallback():
    app, events = _act("open brave", AUDIO, fallback="should not be used")
    assert app.commands == ["open brave"]
    assert ("engine", "windows") in events
    assert ("result", "ran open brave") in events


@windows_only
def test_no_grammar_match_falls_back_to_next_layer():
    app, events = _act("", AUDIO, fallback="Atlas, search the web for cats.")
    assert app.commands == ["search the web for cats"]
    assert ("engine", "cloud") in events


@windows_only
def test_no_match_and_no_fallback_says_so():
    app, events = _act("", AUDIO)
    assert app.commands == []
    assert events[-1] == ("timeout", "Didn't catch a command I know")


@windows_only
def test_silence_after_wake_reports_no_command():
    app, events = _act("", b"", fallback="unused")
    assert app.commands == []
    assert events[-1][0] == "timeout" and "no command" in events[-1][1]


@windows_only
@pytest.mark.skipif(
    os.environ.get("ATLAS_TEST_DESKTOP") != "1",
    reason="Opens the real microphone - set ATLAS_TEST_DESKTOP=1",
)
def test_windows_loop_starts_listening_and_stops_cleanly():
    from atlas.platform.win32.voice import WindowsVoiceLoop

    app = Application()
    app.bootstrap()
    events: list[tuple[str, str]] = []
    loop = WindowsVoiceLoop(app, on_event=lambda k, m: events.append((k, m)))
    loop.start()
    time.sleep(1)
    loop.stop()
    assert loop._thread is not None and not loop._thread.is_alive()
    assert ("status", "sleeping") in events
