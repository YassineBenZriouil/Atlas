import pytest


@pytest.fixture(autouse=True)
def isolated_app_data(tmp_path, monkeypatch):
    """Every test gets its own %APPDATA%\\Atlas so tests never touch the
    real user profile."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
