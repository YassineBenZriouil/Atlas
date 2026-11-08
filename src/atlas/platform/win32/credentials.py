"""SecretStore backed by Windows Credential Manager (generic credentials,
per user, never written to config or logs)."""

from __future__ import annotations

import contextlib

import pywintypes
import win32cred

from atlas.platform.secrets import SecretStore


class CredentialManagerStore(SecretStore):
    def save(self, name: str, secret: str) -> None:
        win32cred.CredWrite(
            {
                "Type": win32cred.CRED_TYPE_GENERIC,
                "TargetName": name,
                "UserName": "atlas",
                "CredentialBlob": secret,
                "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
            }
        )

    def load(self, name: str) -> str | None:
        try:
            credential = win32cred.CredRead(name, win32cred.CRED_TYPE_GENERIC)
        except pywintypes.error:  # not found (or unreadable): nothing stored
            return None
        blob = credential.get("CredentialBlob")
        if blob is None:
            return None
        if isinstance(blob, bytes):
            return blob.decode("utf-16-le", errors="ignore").rstrip("\x00")
        return str(blob)

    def delete(self, name: str) -> None:
        with contextlib.suppress(pywintypes.error):  # already absent
            win32cred.CredDelete(name, win32cred.CRED_TYPE_GENERIC)
