import dataclasses

import pytest


@pytest.fixture(autouse=True)
def isolated_app_data(tmp_path, monkeypatch):
    """Every test gets its own app-data directory so tests never touch the
    real user profile."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))


@pytest.fixture(autouse=True)
def in_memory_secrets(monkeypatch):
    """Tests never read or delete the user's real stored credentials (e.g. a
    signed-in Spotify account)."""
    from tests.fixtures.fakes import FakeSecretStore

    from atlas.integrations.spotify import token_store
    from atlas.platform import get_backend

    backend = dataclasses.replace(get_backend(), secret_store=FakeSecretStore())
    monkeypatch.setattr(token_store, "get_backend", lambda: backend)
