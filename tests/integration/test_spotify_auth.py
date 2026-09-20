"""Real local HTTP server, real HTTP request against it - no Spotify
account or network access needed, since this only tests ATLAS's side of
the OAuth redirect handshake."""

from __future__ import annotations

import threading

import requests

from atlas.integrations.spotify.auth import SpotifyAuthError, wait_for_callback

REDIRECT_URI = "http://127.0.0.1:8892/callback"


def test_callback_captures_code_and_state():
    result: dict[str, object] = {}

    def run() -> None:
        result["params"] = wait_for_callback(REDIRECT_URI, timeout=5)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(0.3)  # let the server bind before we hit it

    response = requests.get(REDIRECT_URI, params={"code": "abc", "state": "xyz"}, timeout=5)
    thread.join(5)

    assert response.status_code == 200
    assert result["params"] == {"code": "abc", "state": "xyz"}


def test_callback_raises_on_authorization_error():
    result: dict[str, object] = {}

    def run() -> None:
        try:
            wait_for_callback(REDIRECT_URI, timeout=5)
        except SpotifyAuthError as exc:
            result["error"] = str(exc)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(0.3)

    requests.get(REDIRECT_URI, params={"error": "access_denied"}, timeout=5)
    thread.join(5)

    assert "access_denied" in result.get("error", "")


def test_callback_times_out_with_no_request():
    with_error: dict[str, object] = {}

    def run() -> None:
        try:
            wait_for_callback(REDIRECT_URI, timeout=0.5)
        except SpotifyAuthError as exc:
            with_error["error"] = str(exc)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(3)

    assert "Timed out" in with_error.get("error", "")
