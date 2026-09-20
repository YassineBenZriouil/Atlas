"""SpeechEngine abstraction (Atlas.md section 5, section 9). Vosk is the
Phase 2 implementation; this interface is what keeps it replaceable."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto

from atlas.speech.result import RecognitionResult


class SpeechMode(Enum):
    WAKE = auto()
    COMMAND = auto()


class SpeechEngine(ABC):
    @abstractmethod
    def set_mode(self, mode: SpeechMode) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def process_audio(self, audio: bytes) -> RecognitionResult | None: ...

    @abstractmethod
    def finalize(self) -> RecognitionResult | None:
        """Force whatever the engine has accumulated so far into a final
        result, without waiting for it to detect an endpoint on its own.
        Called when something else (a silence timeout, the wake controller)
        has already decided the utterance is over."""
        ...
