"""Spotify Web API client (Atlas.md section 27). Talks only to Spotify's
official REST API over HTTPS - never scrapes, never circumvents auth,
never downloads audio."""

from __future__ import annotations

import time
from typing import Any

import requests

from atlas.integrations.spotify.token_store import load_refresh_token
from atlas.logging_setup import get_logger

logger = get_logger("spotify.client")

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_BASE = "https://api.spotify.com/v1"
_REQUEST_TIMEOUT = 10


class SpotifyApiError(RuntimeError):
    pass


class SpotifyNotAuthenticatedError(SpotifyApiError):
    pass


class SpotifyNoActiveDeviceError(SpotifyApiError):
    pass


class SpotifyClient:
    """Access tokens are cached in memory only and refreshed on demand -
    never persisted, since they're short-lived and cheap to re-derive from
    the refresh token (see token_store)."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def _ensure_access_token(self) -> str:
        if self._access_token and time.monotonic() < self._expires_at:
            return self._access_token

        refresh_token = load_refresh_token()
        if not refresh_token:
            raise SpotifyNotAuthenticatedError(
                "Spotify is not connected. Run `atlas --spotify-login` first."
            )

        response = requests.post(
            _TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(self._client_id, self._client_secret),
            timeout=_REQUEST_TIMEOUT,
        )
        if not response.ok:
            raise SpotifyNotAuthenticatedError(
                f"Failed to refresh Spotify token: {response.status_code}"
            )
        payload = response.json()
        self._access_token = payload["access_token"]
        self._expires_at = time.monotonic() + payload.get("expires_in", 3600) - 30
        return self._access_token

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        token = self._ensure_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        response = requests.request(
            method, f"{_API_BASE}{path}", headers=headers, timeout=_REQUEST_TIMEOUT, **kwargs
        )
        if response.status_code == 404 and "NO_ACTIVE_DEVICE" in response.text:
            raise SpotifyNoActiveDeviceError(
                "No active Spotify device - open Spotify on a device first."
            )
        if response.status_code >= 400:
            raise SpotifyApiError(f"Spotify API error {response.status_code}: {response.text}")
        return response

    def play(self) -> None:
        self._request("PUT", "/me/player/play")

    def pause(self) -> None:
        self._request("PUT", "/me/player/pause")

    def next_track(self) -> None:
        self._request("POST", "/me/player/next")

    def previous_track(self) -> None:
        self._request("POST", "/me/player/previous")

    def search_track(self, query: str) -> dict[str, Any] | None:
        response = self._request(
            "GET", "/search", params={"q": query, "type": "track", "limit": 1}
        )
        items = response.json().get("tracks", {}).get("items", [])
        return items[0] if items else None

    def play_uris(self, uris: list[str]) -> None:
        self._request("PUT", "/me/player/play", json={"uris": uris})

    def play_context(self, context_uri: str) -> None:
        self._request("PUT", "/me/player/play", json={"context_uri": context_uri})

    def find_playlist(self, name: str) -> dict[str, Any] | None:
        response = self._request("GET", "/me/playlists", params={"limit": 50})
        for playlist in response.json().get("items", []):
            if name.lower() in playlist["name"].lower():
                return playlist
        return None
