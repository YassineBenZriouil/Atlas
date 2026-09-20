"""Real Windows Credential Manager round-trip - safe (writes/reads/deletes
only ATLAS's own credential entry) and fast."""

from atlas.integrations.spotify.token_store import (
    clear_refresh_token,
    load_refresh_token,
    save_refresh_token,
)


def test_round_trip():
    clear_refresh_token()
    assert load_refresh_token() is None

    save_refresh_token("dummy-refresh-token-for-tests")
    assert load_refresh_token() == "dummy-refresh-token-for-tests"

    clear_refresh_token()
    assert load_refresh_token() is None


def test_overwrite():
    save_refresh_token("first-token")
    save_refresh_token("second-token")
    assert load_refresh_token() == "second-token"
    clear_refresh_token()


def test_clear_when_absent_does_not_raise():
    clear_refresh_token()
    clear_refresh_token()
