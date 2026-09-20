"""Wake-word orchestration (Atlas.md section 8). Detecting the phrase itself
is the WakeDetector's job (Phase 2); this controller only reacts to
wake/timeout events with deterministic state transitions, which is why it
can be fully implemented - and unit tested - in Phase 1."""

from __future__ import annotations

from atlas.application.state import AtlasState, StateMachine
from atlas.logging_setup import get_logger

logger = get_logger("wake")


class WakeController:
    def __init__(self, state_machine: StateMachine) -> None:
        self._state_machine = state_machine

    def on_wake_detected(self) -> None:
        if self._state_machine.state != AtlasState.SLEEPING:
            logger.debug("Wake ignored: not currently SLEEPING")
            return
        logger.info("Wake word detected")
        self._state_machine.transition(AtlasState.WAKE_DETECTED)
        self._state_machine.transition(AtlasState.LISTENING)

    def on_timeout(self) -> None:
        if self._state_machine.state == AtlasState.LISTENING:
            logger.info("Listening timed out; returning to sleep")
            self._state_machine.fail("listening timeout")
            self._state_machine.recover()
