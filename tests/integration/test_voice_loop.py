"""Feeds locally-synthesized speech (silence -> "atlas" -> silence ->
"open brave" -> silence) through VoiceLoop's real frame-processing path -
same wake detector and speech engine the real microphone stream would
drive, just fed synthetic frames instead of live audio. Uses an injected
FakeApplicationManager so "open brave" never launches anything real.
Skips cleanly if no Vosk model is present."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest
from tests.fixtures.fakes import (
    FakeApplicationManager,
    FakeKeyboardController,
    FakeMonitorManager,
    FakeMouseController,
    FakeSystemController,
    FakeWindowManager,
)

from atlas.application.app import Application
from atlas.application.voice_loop import VoiceLoop
from atlas.speech.engine import SpeechMode

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


def _find_model() -> Path | None:
    if not MODELS_DIR.exists():
        return None
    for entry in MODELS_DIR.iterdir():
        if entry.is_dir() and entry.name.startswith("vosk-model"):
            return entry
    return None


MODEL_PATH = _find_model()

requires_model = pytest.mark.skipif(
    MODEL_PATH is None,
    reason="No Vosk model found under models/ - see models/README.md.",
)


def _synthesize(text: str, path: Path) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    engine.save_to_file(text, str(path))
    engine.runAndWait()


def _load_pcm_16k_mono(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wav_file:
        rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        frames = wav_file.readframes(wav_file.getnframes())

    samples = np.frombuffer(frames, dtype=np.int16)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1).astype(np.int16)

    if rate != 16000:
        duration = len(samples) / rate
        target_n = int(duration * 16000)
        original_x = np.linspace(0, duration, num=len(samples))
        target_x = np.linspace(0, duration, num=target_n)
        samples = np.interp(target_x, original_x, samples).astype(np.int16)

    return samples.tobytes()


def _silence(seconds: float, sample_rate: int = 16000) -> bytes:
    return b"\x00\x00" * int(seconds * sample_rate)


def make_app() -> tuple[Application, FakeApplicationManager]:
    window_manager = FakeWindowManager()
    app_manager = FakeApplicationManager(window_manager)
    app = Application(
        window_manager=window_manager,
        monitor_manager=FakeMonitorManager(),
        keyboard_controller=FakeKeyboardController(),
        mouse_controller=FakeMouseController(),
        system_controller=FakeSystemController(),
        application_manager=app_manager,
    )
    app.bootstrap()
    return app, app_manager


@requires_model
def test_wake_then_command_executes_end_to_end(tmp_path):
    wake_wav = tmp_path / "atlas.wav"
    command_wav = tmp_path / "open_brave.wav"
    _synthesize("atlas", wake_wav)
    _synthesize("open brave", command_wav)

    audio = (
        _silence(0.3)
        + _load_pcm_16k_mono(wake_wav)
        + _silence(0.5)
        + _load_pcm_16k_mono(command_wav)
        + _silence(3.0)
    )

    app, app_manager = make_app()
    events: list[tuple[str, str]] = []

    loop = VoiceLoop(
        app=app,
        model_path=str(MODEL_PATH),
        # Generous on purpose: firing wake as soon as the phrase appears in
        # a partial result (rather than waiting for AcceptWaveform to
        # complete) means some trailing wake-clip audio can land in the
        # command-listening phase here - a synthetic-buffer artifact, not
        # a real-microphone one - so the timeout needs slack to absorb it.
        listen_timeout_seconds=2.5,
        on_event=lambda kind, message: events.append((kind, message)),
    )
    # Drive the same code start() would, without opening a real microphone.
    loop._wake_detector.start()
    loop._speech_engine.start()
    loop._speech_engine.set_mode(SpeechMode.COMMAND)
    loop._running = True

    blocksize_bytes = 8000 * 2
    for i in range(0, len(audio), blocksize_bytes):
        loop._on_frame(audio[i : i + blocksize_bytes])

    kinds = [kind for kind, _ in events]
    assert "wake" in kinds
    assert "heard" in kinds
    heard_text = next(message for kind, message in events if kind == "heard")
    assert "brave" in heard_text
    assert app_manager.is_running("brave")
