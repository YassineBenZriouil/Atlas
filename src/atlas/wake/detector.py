"""WakeDetector abstraction (Atlas.md section 8). Phase 2 implements this
using constrained offline speech recognition rather than a separate neural
wake-word product."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class WakeDetector(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def process_audio(self, audio: bytes) -> bool: ...

    @abstractmethod
    def on_wake(self, callback: Callable[[], None]) -> None: ...
