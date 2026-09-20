"""Vosk-backed SpeechEngine (Atlas.md section 5). Fully wired in Phase 2
(section 79, Phase 2 step 2); Phase 1 validates configuration and exposes
the correct shape so the rest of the pipeline can be built and tested
against it without a model or microphone present."""

from __future__ import annotations

from pathlib import Path

from atlas.speech.engine import SpeechEngine, SpeechMode
from atlas.speech.result import RecognitionResult


class SpeechEngineError(RuntimeError):
    pass


class VoskSpeechEngine(SpeechEngine):
    def __init__(self, model_path: str | Path, sample_rate: int = 16000) -> None:
        self._model_path = Path(model_path)
        self._sample_rate = sample_rate
        self._mode = SpeechMode.WAKE

    def set_mode(self, mode: SpeechMode) -> None:
        self._mode = mode

    def start(self) -> None:
        if not self._model_path.exists():
            raise SpeechEngineError(
                f"Vosk model not found at {self._model_path}. Download a model "
                "into the models/ directory before starting speech recognition."
            )
        raise NotImplementedError("The Vosk recognition loop is implemented in Phase 2")

    def stop(self) -> None:
        raise NotImplementedError("Implemented in Phase 2")

    def process_audio(self, audio: bytes) -> RecognitionResult | None:
        raise NotImplementedError("Implemented in Phase 2")
