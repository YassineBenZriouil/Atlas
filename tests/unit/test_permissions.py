from atlas.security.permissions import is_dangerous, requires_confirmation


def test_shutdown_is_dangerous():
    assert is_dangerous("shutdown_computer")


def test_unknown_command_not_dangerous():
    assert not is_dangerous("atlas_status")


def test_dangerous_requires_confirmation_when_enabled():
    assert requires_confirmation("shutdown_computer", confirmations_enabled=True)


def test_dangerous_confirmation_can_be_disabled():
    assert not requires_confirmation("shutdown_computer", confirmations_enabled=False)


def test_safe_command_never_requires_confirmation():
    assert not requires_confirmation("atlas_status", confirmations_enabled=True)
