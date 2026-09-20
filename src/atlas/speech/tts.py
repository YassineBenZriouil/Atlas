"""Local text-to-speech (Atlas.md section 32). ATLAS must work perfectly
with TTS disabled, hence DisabledTTSProvider rather than a None check
scattered through every caller."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pyttsx3


class TTSProvider(ABC):
    @abstractmethod
    def speak(self, text: str) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...


class Pyttsx3TTSProvider(TTSProvider):
    def __init__(self, voice: str = "default", volume: float = 1.0) -> None:
        self._engine = pyttsx3.init()
        self._engine.setProperty("volume", max(0.0, min(1.0, volume)))
        if voice and voice != "default":
            for candidate in self._engine.getProperty("voices"):
                if voice.lower() in (candidate.name or "").lower():
                    self._engine.setProperty("voice", candidate.id)
                    break

    def speak(self, text: str) -> None:
        self._engine.say(text)
        self._engine.runAndWait()

    def stop(self) -> None:
        self._engine.stop()


class DisabledTTSProvider(TTSProvider):
    def speak(self, text: str) -> None:
        pass

    def stop(self) -> None:
        pass


def create_tts_provider(
    *, enabled: bool, voice: str = "default", volume: float = 1.0
) -> TTSProvider:
    if not enabled:
        return DisabledTTSProvider()
    return Pyttsx3TTSProvider(voice=voice, volume=volume)
