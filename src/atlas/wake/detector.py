"""WakeDetector abstraction (Atlas.md section 8), plus a Vosk-backed
implementation using a grammar constrained to just the wake phrase (and an
"unknown" catch-all) rather than a separate neural wake-word product."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

import vosk


class WakeDetector(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def process_audio(self, audio: bytes) -> bool: ...

    @abstractmethod
    def on_wake(self, callback: Callable[[], None]) -> None: ...


class VoskWakeDetector(WakeDetector):
    def __init__(
        self,
        model_path: str | Path,
        wake_phrase: str = "atlas",
        sample_rate: int = 16000,
    ) -> None:
        self._model_path = Path(model_path)
        self._wake_phrase = wake_phrase.lower()
        self._sample_rate = sample_rate
        self._model: vosk.Model | None = None
        self._recognizer: vosk.KaldiRecognizer | None = None
        self._grammar: str = json.dumps([self._wake_phrase, "[unk]"])
        self._callbacks: list[Callable[[], None]] = []

    def on_wake(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def start(self) -> None:
        if not self._model_path.exists():
            raise FileNotFoundError(f"Vosk model not found at {self._model_path}")
        if self._model is None:
            vosk.SetLogLevel(-1)
            self._model = vosk.Model(str(self._model_path))
        self._recognizer = vosk.KaldiRecognizer(self._model, self._sample_rate, self._grammar)

    def stop(self) -> None:
        self._recognizer = None

    def process_audio(self, audio: bytes) -> bool:
        """Checks the *partial* result on every call, not just when
        AcceptWaveform completes an utterance - some models/grammar
        combinations never naturally return an endpoint for a single short
        word (confirmed: the wake phrase shows up correctly in
        PartialResult() well before AcceptWaveform ever returns True), so
        relying only on AcceptWaveform silently never detects the wake
        word at all with those models."""
        if self._recognizer is None:
            return False

        if self._recognizer.AcceptWaveform(audio):
            text = json.loads(self._recognizer.Result()).get("text", "")
        else:
            text = json.loads(self._recognizer.PartialResult()).get("partial", "")

        detected = self._wake_phrase in text
        if detected:
            assert self._model is not None
            # Fresh recognizer so the same lingering partial doesn't fire
            # again on the very next frame.
            self._recognizer = vosk.KaldiRecognizer(self._model, self._sample_rate, self._grammar)
            for callback in self._callbacks:
                callback()
        return detected
