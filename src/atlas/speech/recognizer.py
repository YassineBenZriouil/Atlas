"""Wraps a SpeechEngine with the wake/command grammar-restriction switch
(Atlas.md section 9)."""

from __future__ import annotations

from atlas.speech.engine import SpeechEngine, SpeechMode
from atlas.speech.result import RecognitionResult


class Recognizer:
    def __init__(self, engine: SpeechEngine) -> None:
        self._engine = engine
        self._mode = SpeechMode.WAKE

    @property
    def mode(self) -> SpeechMode:
        return self._mode

    def set_mode(self, mode: SpeechMode) -> None:
        self._mode = mode
        self._engine.set_mode(mode)

    def start(self) -> None:
        self._engine.start()

    def stop(self) -> None:
        self._engine.stop()

    def process_audio(self, audio: bytes) -> RecognitionResult | None:
        return self._engine.process_audio(audio)
