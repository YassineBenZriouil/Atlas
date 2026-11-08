from __future__ import annotations

import io
import sys
import wave

import pytest
import requests

from atlas.application.voice_loop import strip_wake_phrase
from atlas.config.schema import SpeechConfig
from atlas.speech.cloud import CloudTranscriber
from atlas.speech.transcriber import (
    Transcriber,
    TranscriberChain,
    TranscriberError,
    create_transcriber_chain,
)


class FakeTranscriber(Transcriber):
    def __init__(self, name: str, text: str = "", error: bool = False) -> None:
        self.name = name
        self._text = text
        self._error = error
        self.calls = 0

    def transcribe(self, pcm: bytes, sample_rate: int) -> str:
        self.calls += 1
        if self._error:
            raise TranscriberError("boom")
        return self._text


def test_first_provider_with_text_wins():
    second = FakeTranscriber("cloud", "unused")
    chain = TranscriberChain([FakeTranscriber("native", "open brave"), second])
    assert chain.transcribe(b"", 16000, "local") == ("open brave", "native")
    assert second.calls == 0


def test_error_and_empty_fall_through_to_next():
    chain = TranscriberChain(
        [FakeTranscriber("native", error=True), FakeTranscriber("cloud", "  mute  ")]
    )
    assert chain.transcribe(b"", 16000, "local") == ("mute", "cloud")
    chain = TranscriberChain([FakeTranscriber("native", "")])
    assert chain.transcribe(b"", 16000, "local") == ("local", "vosk")


def test_empty_chain_uses_local_text():
    assert TranscriberChain([]).transcribe(b"", 16000, "status") == ("status", "vosk")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Atlas, open brave", "open brave"),
        ("atlas open brave", "open brave"),
        ("open atlas", "open atlas"),
        ("open brave", "open brave"),
    ],
)
def test_strip_wake_phrase(text, expected):
    assert strip_wake_phrase(text, "atlas") == expected


def test_cloud_skipped_without_api_key(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.delenv("ATLAS_STT_API_KEY", raising=False)
    chain = create_transcriber_chain(SpeechConfig(providers=["cloud", "bogus"]))
    assert chain.transcribers == []


def test_cloud_added_with_api_key(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ATLAS_STT_API_KEY", "sk-test")
    chain = create_transcriber_chain(SpeechConfig(providers=["cloud"]))
    assert [t.name for t in chain.transcribers] == ["cloud"]


def test_native_skipped_without_a_native_backend(monkeypatch):
    import atlas.platform

    monkeypatch.setattr(atlas.platform, "get_backend", atlas.platform._fallback_backend)
    assert create_transcriber_chain(SpeechConfig(providers=["native"])).transcribers == []


class FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_cloud_posts_wav_with_bearer_and_language(monkeypatch):
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(200, {"text": "open brave"})

    monkeypatch.setattr(requests, "post", fake_post)
    cloud = CloudTranscriber("https://x/v1/audio/transcriptions", "sk", model="m", language="en-us")
    assert cloud.transcribe(b"\x01\x00" * 160, 16000) == "open brave"
    assert captured["headers"] == {"Authorization": "Bearer sk"}
    assert captured["data"] == {"model": "m", "language": "en"}
    wav_bytes = captured["files"]["file"][1]
    with wave.open(io.BytesIO(wav_bytes)) as wav_file:
        assert (wav_file.getframerate(), wav_file.getnchannels(), wav_file.getnframes()) == (
            16000,
            1,
            160,
        )


@pytest.mark.parametrize(
    "outcome",
    [
        requests.ConnectionError("offline"),
        FakeResponse(401, {}),
        FakeResponse(200, ValueError("not json")),
    ],
)
def test_cloud_failures_raise_transcriber_error(monkeypatch, outcome):
    def fake_post(url, **kwargs):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(requests, "post", fake_post)
    cloud = CloudTranscriber("https://x", "sk", model="m")
    with pytest.raises(TranscriberError):
        cloud.transcribe(b"", 16000)


@pytest.mark.skipif(sys.platform != "win32", reason="SAPI is Windows-only")
def test_sapi_transcribes_synthesized_speech(tmp_path):
    """Real round trip: SAPI TTS -> 16 kHz WAV -> in-memory SAPI dictation."""
    import win32com.client

    from atlas.platform.win32.sapi import SapiTranscriber

    path = tmp_path / "utterance.wav"
    audio_format = win32com.client.Dispatch("SAPI.SpAudioFormat")
    audio_format.Type = 18  # 16 kHz 16-bit mono
    file_stream = win32com.client.Dispatch("SAPI.SpFileStream")
    file_stream.Format = audio_format
    file_stream.Open(str(path), 3)
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    voice.AudioOutputStream = file_stream
    voice.Speak("open visual studio code")
    file_stream.Close()
    with wave.open(str(path)) as wav_file:
        pcm = wav_file.readframes(wav_file.getnframes())

    text = SapiTranscriber().transcribe(pcm, 16000)
    assert "visual studio code" in text.lower()
