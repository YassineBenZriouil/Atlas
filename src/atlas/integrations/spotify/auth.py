"""Spotify OAuth - Authorization Code flow (Atlas.md sections 27, 59). Run
once interactively (`atlas --spotify-login`); after that ATLAS holds only
a refresh token (atlas.integrations.spotify.token_store) and renews access
tokens silently. Never circumvents Spotify's own authentication."""

from __future__ import annotations

import http.server
import secrets
import threading
import urllib.parse
import webbrowser
from dataclasses import dataclass

import requests

from atlas.integrations.spotify.token_store import save_refresh_token
from atlas.logging_setup import get_logger

logger = get_logger("spotify.auth")

_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
_TOKEN_URL = "https://accounts.spotify.com/api/token"
_REQUEST_TIMEOUT = 10
SCOPES = (
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
)


class SpotifyAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpotifyCredentials:
    client_id: str
    client_secret: str
    redirect_uri: str


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - required name for BaseHTTPRequestHandler
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        self.server.callback_params = params  # type: ignore[attr-defined]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        message = (
            "Signed in - you can close this tab and return to ATLAS."
            if "code" in params
            else "Spotify sign-in failed - you can close this tab."
        )
        self.wfile.write(f"<html><body><p>{message}</p></body></html>".encode())

    def log_message(self, log_format: str, *args: object) -> None:
        pass  # keep stdout clean; nothing here needs per-request logging


def wait_for_callback(redirect_uri: str, timeout: float = 120.0) -> dict[str, str]:
    """Runs a one-shot local HTTP server on the redirect URI's host/port and
    blocks until exactly one request arrives (Spotify's redirect) or the
    timeout expires."""
    parsed = urllib.parse.urlparse(redirect_uri)
    server = http.server.HTTPServer(
        (parsed.hostname or "127.0.0.1", parsed.port or 80), _CallbackHandler
    )
    server.callback_params = {}  # type: ignore[attr-defined]
    server.timeout = timeout

    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    thread.join(timeout + 1)
    server.server_close()

    params: dict[str, str] = getattr(server, "callback_params", {})
    if not params:
        raise SpotifyAuthError("Timed out waiting for Spotify's redirect")
    if "error" in params:
        raise SpotifyAuthError(f"Spotify authorization failed: {params['error']}")
    if "code" not in params:
        raise SpotifyAuthError("Spotify's redirect did not include an authorization code")
    return params


def build_authorize_url(credentials: SpotifyCredentials, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": credentials.client_id,
            "response_type": "code",
            "redirect_uri": credentials.redirect_uri,
            "scope": " ".join(SCOPES),
            "state": state,
        }
    )
    return f"{_AUTHORIZE_URL}?{query}"


def exchange_code_for_tokens(credentials: SpotifyCredentials, code: str) -> dict[str, object]:
    response = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": credentials.redirect_uri,
        },
        auth=(credentials.client_id, credentials.client_secret),
        timeout=_REQUEST_TIMEOUT,
    )
    if not response.ok:
        raise SpotifyAuthError(f"Token exchange failed: {response.status_code} {response.text}")
    return response.json()  # type: ignore[no-any-return]


def run_login_flow(credentials: SpotifyCredentials) -> None:
    state = secrets.token_urlsafe(16)
    authorize_url = build_authorize_url(credentials, state)

    logger.info("Opening browser for Spotify sign-in")
    webbrowser.open(authorize_url)

    params = wait_for_callback(credentials.redirect_uri)
    if params.get("state") != state:
        raise SpotifyAuthError("State mismatch on Spotify's redirect - possible CSRF; aborting")

    payload = exchange_code_for_tokens(credentials, params["code"])
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        raise SpotifyAuthError("Spotify did not return a refresh token")

    save_refresh_token(str(refresh_token))
    logger.info("Spotify sign-in complete; refresh token stored securely")
