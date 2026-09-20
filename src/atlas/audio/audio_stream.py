"""Streaming audio frame abstraction feeding the wake detector / speech
engine (Atlas.md section 6)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class AudioStream(ABC):
    @abstractmethod
    def start(self, on_frame: Callable[[bytes], None]) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...
