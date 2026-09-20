"""Spotify integration (Atlas.md sections 27, 59). Optional; disables
itself cleanly if client credentials or a stored refresh token are
missing - Spotify is never required for ATLAS core functionality."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from atlas.commands.registry import CommandRegistry
from atlas.integrations.spotify import commands as spotify_commands
from atlas.integrations.spotify.client import SpotifyClient
from atlas.integrations.spotify.token_store import load_refresh_token
from atlas.plugins.base import AtlasPlugin, PluginContext


class SpotifyPlugin(AtlasPlugin):
    name = "spotify"

    def __init__(self) -> None:
        self._client: SpotifyClient | None = None

    def initialize(self, context: PluginContext) -> None:
        load_dotenv()
        client_id = os.environ.get("ATLAS_SPOTIFY_CLIENT_ID", "")
        client_secret = os.environ.get("ATLAS_SPOTIFY_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise RuntimeError(
                "ATLAS_SPOTIFY_CLIENT_ID/ATLAS_SPOTIFY_CLIENT_SECRET not set (see .env.example)"
            )
        if load_refresh_token() is None:
            raise RuntimeError("Spotify not authenticated; run `atlas --spotify-login`")
        self._client = SpotifyClient(client_id, client_secret)

    def register_commands(self, registry: CommandRegistry) -> None:
        spotify_commands.register(registry)

    def shutdown(self) -> None:
        self._client = None

    @property
    def client(self) -> SpotifyClient:
        assert self._client is not None, "SpotifyPlugin.initialize() has not run"
        return self._client


PLUGIN_CLASS = SpotifyPlugin
