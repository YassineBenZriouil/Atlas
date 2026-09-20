"""Microphone abstraction (Atlas.md section 7), plus the sounddevice-backed
implementation.

This class owns device *selection*, not audio streaming - that's
atlas.audio.audio_stream.AudioStream. start()/stop() here are no-ops for
the sounddevice backend because there is nothing to start until an
AudioStream is opened against the selected device; they exist so a future
backend that needs an explicit handle can use them without changing the
interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import sounddevice as sd

from atlas.audio.devices import AudioDevice


class Microphone(ABC):
    @abstractmethod
    def list_devices(self) -> list[AudioDevice]: ...

    @abstractmethod
    def open(self, device_id: str) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...


class SoundDeviceMicrophone(Microphone):
    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._device_id: int | None = None

    def list_devices(self) -> list[AudioDevice]:
        devices: list[AudioDevice] = []
        for index, info in enumerate(sd.query_devices()):
            if info.get("max_input_channels", 0) > 0:
                devices.append(
                    AudioDevice(
                        device_id=str(index),
                        name=info["name"],
                        max_input_channels=info["max_input_channels"],
                        default_sample_rate=int(info["default_samplerate"]),
                    )
                )
        return devices

    def open(self, device_id: str) -> None:
        if device_id == "default":
            self._device_id = None
            return
        self._device_id = int(device_id)

    def close(self) -> None:
        self._device_id = None

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    @property
    def device_id(self) -> int | None:
        return self._device_id

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def channels(self) -> int:
        return self._channels
