import pytest

from atlas.application.state import AtlasState, InvalidTransitionError, StateMachine


def test_initial_state_is_sleeping():
    sm = StateMachine()
    assert sm.state is AtlasState.SLEEPING


def test_full_happy_path():
    sm = StateMachine()
    for target in (
        AtlasState.WAKE_DETECTED,
        AtlasState.LISTENING,
        AtlasState.RECOGNIZING,
        AtlasState.PARSING,
        AtlasState.VALIDATING,
        AtlasState.EXECUTING,
        AtlasState.FEEDBACK,
        AtlasState.SLEEPING,
    ):
        sm.transition(target)
    assert sm.state is AtlasState.SLEEPING


def test_invalid_transition_raises():
    sm = StateMachine()
    with pytest.raises(InvalidTransitionError):
        sm.transition(AtlasState.EXECUTING)


def test_fail_and_recover_from_any_state():
    sm = StateMachine()
    sm.transition(AtlasState.WAKE_DETECTED)
    sm.fail("boom")
    assert sm.state is AtlasState.ERROR
    sm.recover()
    assert sm.state is AtlasState.SLEEPING


def test_recover_only_valid_from_error():
    sm = StateMachine()
    with pytest.raises(InvalidTransitionError):
        sm.recover()


def test_listeners_are_notified():
    events = []
    sm = StateMachine()
    sm.on_change(lambda prev, cur: events.append((prev, cur)))
    sm.transition(AtlasState.WAKE_DETECTED)
    assert events == [(AtlasState.SLEEPING, AtlasState.WAKE_DETECTED)]
