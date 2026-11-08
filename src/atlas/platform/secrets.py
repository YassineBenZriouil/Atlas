"""Secure storage for small secrets (refresh tokens), backed by the OS
credential store - never config files or logs (Atlas.md section 59)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SecretStore(ABC):
    @abstractmethod
    def save(self, name: str, secret: str) -> None: ...

    @abstractmethod
    def load(self, name: str) -> str | None:
        """None when nothing is stored under `name`."""
        ...

    @abstractmethod
    def delete(self, name: str) -> None:
        """No-op when nothing is stored under `name`."""
        ...
