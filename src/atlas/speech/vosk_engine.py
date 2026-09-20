"""Vosk-backed SpeechEngine (Atlas.md section 5)."""

from __future__ import annotations

import json
from pathlib import Path

import vosk

from atlas.speech.engine import SpeechEngine, SpeechMode
from atlas.speech.result import RecognitionResult
from atlas.utils.paths import get_models_dir


class SpeechEngineError(RuntimeError):
    pass


def find_default_model(configured_path: str = "") -> Path | None:
    """Configured path first; otherwise the first `vosk-model*` directory
    found in the project-local `models/` folder or the per-user models
    directory (Atlas.md section 53's model-install step isn't automated
    until Phase 3, so both locations are checked by hand for now)."""
    if configured_path:
        path = Path(configured_path)
        if path.exists():
            return path

    for base in (Path("models"), get_models_dir()):
        if not base.exists():
            continue
        for entry in sorted(base.iterdir()):
            if entry.is_dir() and entry.name.startswith("vosk-model"):
                return entry
    return None


class VoskSpeechEngine(SpeechEngine):
    """Confidence is a heuristic, not a real acoustic score: Vosk's default
    JSON output carries no per-utterance confidence, so final results are
    reported at 1.0 and in-progress partials at 0.5. This is enough for
    ATLAS's deterministic pipeline, which never uses confidence to guess -
    only the exact matched text ever reaches the parser."""

    def __init__(self, model_path: str | Path, sample_rate: int = 16000) -> None:
        self._model_path = Path(model_path)
        self._sample_rate = sample_rate
        self._mode = SpeechMode.WAKE
        self._model: vosk.Model | None = None
        self._recognizer: vosk.KaldiRecognizer | None = None

    def set_mode(self, mode: SpeechMode) -> None:
        self._mode = mode
        if self._model is not None:
            self._recognizer = vosk.KaldiRecognizer(self._model, self._sample_rate)

    def start(self) -> None:
        if not self._model_path.exists():
            raise SpeechEngineError(
                f"Vosk model not found at {self._model_path}. Download a model "
                "into the models/ directory before starting speech recognition."
            )
        if self._model is None:
            vosk.SetLogLevel(-1)
            self._model = vosk.Model(str(self._model_path))
        self._recognizer = vosk.KaldiRecognizer(self._model, self._sample_rate)

    def stop(self) -> None:
        self._recognizer = None

    def process_audio(self, audio: bytes) -> RecognitionResult | None:
        if self._recognizer is None:
            raise SpeechEngineError("Engine not started")

        if self._recognizer.AcceptWaveform(audio):
            text = json.loads(self._recognizer.Result()).get("text", "")
            if not text:
                return None
            return RecognitionResult(text=text, confidence=1.0, is_final=True)

        partial = json.loads(self._recognizer.PartialResult()).get("partial", "")
        if not partial:
            return None
        return RecognitionResult(text=partial, confidence=0.5, is_final=False)

    def finalize(self) -> RecognitionResult | None:
        if self._recognizer is None:
            return None
        text = json.loads(self._recognizer.FinalResult()).get("text", "")
        if not text:
            return None
        return RecognitionResult(text=text, confidence=1.0, is_final=True)
