"""Token store round-trips (through the in-memory store from conftest), plus
one real Credential Manager round-trip under a test-only name, so the
user's actual Spotify credential is never touched."""

import sys

import pytest

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


def test_clear_when_absent_does_not_raise():
    clear_refresh_token()
    clear_refresh_token()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Credential Manager")
def test_credential_manager_round_trip():
    from atlas.platform.win32.credentials import CredentialManagerStore

    store, name = CredentialManagerStore(), "Atlas/Test/PytestOnly"
    store.delete(name)
    assert store.load(name) is None
    store.save(name, "secret-1")
    store.save(name, "secret-2")
    assert store.load(name) == "secret-2"
    store.delete(name)
    store.delete(name)
    assert store.load(name) is None
