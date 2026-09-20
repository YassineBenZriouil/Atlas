"""Mouse automation abstraction (Atlas.md section 25). Absolute-coordinate
voice commands are explicitly out of scope for the initial release."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MouseController(ABC):
    @abstractmethod
    def click(self) -> None: ...

    @abstractmethod
    def double_click(self) -> None: ...

    @abstractmethod
    def right_click(self) -> None: ...

    @abstractmethod
    def move_relative(self, dx: int, dy: int) -> None: ...

    @abstractmethod
    def scroll(self, amount: int) -> None: ...
