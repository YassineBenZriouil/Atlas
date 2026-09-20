"""Streaming audio frame abstraction feeding the wake detector / speech
engine (Atlas.md section 6), plus the sounddevice-backed implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

import sounddevice as sd

from atlas.audio.microphone import SoundDeviceMicrophone
from atlas.logging_setup import get_logger

logger = get_logger("audio")


class AudioStream(ABC):
    @abstractmethod
    def start(self, on_frame: Callable[[bytes], None]) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...


class SoundDeviceAudioStream(AudioStream):
    """Raw 16-bit mono PCM frames, matching what Vosk expects, at whatever
    block size the caller chooses (smaller = lower latency, more callbacks)."""

    def __init__(self, microphone: SoundDeviceMicrophone, blocksize: int = 8000) -> None:
        self._microphone = microphone
        self._blocksize = blocksize
        self._stream: sd.RawInputStream | None = None

    def start(self, on_frame: Callable[[bytes], None]) -> None:
        def _callback(indata: bytes, _frames: int, _time_info: object, status: object) -> None:
            if status:
                logger.warning("Audio stream status: %s", status)
            on_frame(bytes(indata))

        self._stream = sd.RawInputStream(
            samplerate=self._microphone.sample_rate,
            blocksize=self._blocksize,
            dtype="int16",
            channels=self._microphone.channels,
            device=self._microphone.device_id,
            callback=_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
