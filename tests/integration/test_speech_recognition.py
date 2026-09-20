"""Exercises the real Vosk engine and wake detector against locally
synthesized speech (via the TTS engine) - no network access, no human
speaker required, and no test hardware assumptions beyond a downloaded
model. Skips cleanly if no model is present (models/ is gitignored)."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from atlas.wake.detector import VoskWakeDetector

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
    reason="No Vosk model found under models/ - download one to run this test "
    "(see models/README.md).",
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


@requires_model
def test_wake_detector_hears_wake_phrase(tmp_path):
    wav_path = tmp_path / "atlas.wav"
    _synthesize("atlas", wav_path)
    audio = _load_pcm_16k_mono(wav_path)

    detector = VoskWakeDetector(MODEL_PATH, wake_phrase="atlas")
    detector.start()
    events = []
    detector.on_wake(lambda: events.append(True))
    for i in range(0, len(audio), 4000):
        detector.process_audio(audio[i : i + 4000])

    assert events, "expected the wake detector to fire on synthesized 'atlas'"


@requires_model
def test_wake_detector_does_not_false_trigger(tmp_path):
    wav_path = tmp_path / "open_brave.wav"
    _synthesize("open brave", wav_path)
    audio = _load_pcm_16k_mono(wav_path)

    detector = VoskWakeDetector(MODEL_PATH, wake_phrase="atlas")
    detector.start()
    events = []
    detector.on_wake(lambda: events.append(True))
    for i in range(0, len(audio), 4000):
        detector.process_audio(audio[i : i + 4000])

    assert not events, "wake detector should not fire on unrelated speech"


@requires_model
def test_speech_engine_transcribes_command(tmp_path):
    from atlas.speech.vosk_engine import VoskSpeechEngine

    wav_path = tmp_path / "open_brave.wav"
    _synthesize("open brave", wav_path)
    audio = _load_pcm_16k_mono(wav_path)

    engine = VoskSpeechEngine(MODEL_PATH)
    engine.start()
    for i in range(0, len(audio), 4000):
        engine.process_audio(audio[i : i + 4000])
    final = engine.finalize()

    assert final is not None
    assert final.is_final
    assert "brave" in final.text
