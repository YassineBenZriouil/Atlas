"""The ATLAS state machine (Atlas.md section 33). Deterministic, finite,
testable - no "understanding", just transitions."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto

from atlas.logging_setup import get_logger

logger = get_logger("state")

StateListener = Callable[["AtlasState", "AtlasState"], None]


class AtlasState(Enum):
    SLEEPING = auto()
    WAKE_DETECTED = auto()
    LISTENING = auto()
    RECOGNIZING = auto()
    PARSING = auto()
    VALIDATING = auto()
    EXECUTING = auto()
    FEEDBACK = auto()
    ERROR = auto()
    RECOVERY = auto()
    DISABLED = auto()


_VALID_TRANSITIONS: dict[AtlasState, frozenset[AtlasState]] = {
    AtlasState.SLEEPING: frozenset({AtlasState.WAKE_DETECTED, AtlasState.DISABLED}),
    AtlasState.WAKE_DETECTED: frozenset({AtlasState.LISTENING}),
    AtlasState.LISTENING: frozenset({AtlasState.RECOGNIZING}),
    AtlasState.RECOGNIZING: frozenset({AtlasState.PARSING}),
    AtlasState.PARSING: frozenset({AtlasState.VALIDATING}),
    AtlasState.VALIDATING: frozenset({AtlasState.EXECUTING}),
    AtlasState.EXECUTING: frozenset({AtlasState.FEEDBACK}),
    AtlasState.FEEDBACK: frozenset({AtlasState.SLEEPING}),
    AtlasState.ERROR: frozenset({AtlasState.RECOVERY}),
    AtlasState.RECOVERY: frozenset({AtlasState.SLEEPING}),
    AtlasState.DISABLED: frozenset({AtlasState.SLEEPING}),
}


class InvalidTransitionError(RuntimeError):
    pass


class StateMachine:
    """Any state may transition to ERROR via `fail()`; every other transition
    must follow `_VALID_TRANSITIONS`."""

    def __init__(self, initial: AtlasState = AtlasState.SLEEPING) -> None:
        self._state = initial
        self._listeners: list[StateListener] = []

    @property
    def state(self) -> AtlasState:
        return self._state

    def on_change(self, listener: StateListener) -> None:
        self._listeners.append(listener)

    def _set(self, previous: AtlasState, target: AtlasState) -> None:
        self._state = target
        logger.debug("State transition: %s -> %s", previous.name, target.name)
        for listener in self._listeners:
            listener(previous, target)

    def transition(self, target: AtlasState) -> None:
        allowed = _VALID_TRANSITIONS.get(self._state, frozenset())
        if target not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition from {self._state.name} to {target.name}"
            )
        self._set(self._state, target)

    def fail(self, reason: str = "") -> None:
        previous = self._state
        logger.error("State machine entered ERROR from %s: %s", previous.name, reason)
        self._set(previous, AtlasState.ERROR)

    def recover(self) -> None:
        if self._state != AtlasState.ERROR:
            raise InvalidTransitionError("recover() is only valid from ERROR")
        self._set(self._state, AtlasState.RECOVERY)
        self._set(self._state, AtlasState.SLEEPING)
