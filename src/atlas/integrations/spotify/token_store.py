"""Spotify refresh-token storage in the OS credential store (Atlas.md
section 59). The access token is never persisted - it's short-lived and
cheap to re-derive from the refresh token."""

from __future__ import annotations

from atlas.platform import get_backend

_TARGET_NAME = "Atlas/Spotify/RefreshToken"


def save_refresh_token(refresh_token: str) -> None:
    get_backend().secret_store.save(_TARGET_NAME, refresh_token)


def load_refresh_token() -> str | None:
    return get_backend().secret_store.load(_TARGET_NAME)


def clear_refresh_token() -> None:
    get_backend().secret_store.delete(_TARGET_NAME)
