"""Secure refresh-token storage via Windows Credential Manager (Atlas.md
section 59: credentials/tokens must be stored securely, never in
plaintext config or logs). The access token is never persisted - it's
short-lived and cheap to re-derive from the refresh token, so keeping it
only in memory avoids one more place a secret could leak."""

from __future__ import annotations

import contextlib

import win32cred

_TARGET_NAME = "Atlas/Spotify/RefreshToken"


def save_refresh_token(refresh_token: str) -> None:
    win32cred.CredWrite(
        {
            "Type": win32cred.CRED_TYPE_GENERIC,
            "TargetName": _TARGET_NAME,
            "UserName": "atlas",
            "CredentialBlob": refresh_token,
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
        }
    )


def load_refresh_token() -> str | None:
    try:
        credential = win32cred.CredRead(_TARGET_NAME, win32cred.CRED_TYPE_GENERIC)
    except Exception:  # noqa: BLE001 - "no credential stored" is not exceptional here
        return None

    blob = credential.get("CredentialBlob")
    if blob is None:
        return None
    if isinstance(blob, bytes):
        return blob.decode("utf-16-le", errors="ignore").rstrip("\x00")
    return str(blob)


def clear_refresh_token() -> None:
    with contextlib.suppress(Exception):
        win32cred.CredDelete(_TARGET_NAME, win32cred.CRED_TYPE_GENERIC)
