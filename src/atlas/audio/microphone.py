"""Microphone abstraction (Atlas.md section 7). Device enumeration/capture
via sounddevice is implemented in Phase 2."""

from __future__ import annotations

from abc import ABC, abstractmethod

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
