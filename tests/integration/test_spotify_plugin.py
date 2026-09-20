"""Real plugin isolation behavior (Atlas.md sections 27, 44, 59) - no
mocking of the plugin loader itself, since the whole point is proving
ATLAS keeps running cleanly with Spotify unconfigured, exactly as a real
install without a Spotify account would see it."""

from __future__ import annotations

from atlas.commands.registry import CommandRegistry
from atlas.integrations.spotify import SpotifyPlugin
from atlas.integrations.spotify.token_store import clear_refresh_token, save_refresh_token
from atlas.plugins.loader import PluginLoader
from atlas.plugins.registry import PluginRegistry, PluginStatus


def test_disables_cleanly_without_credentials(monkeypatch):
    monkeypatch.delenv("ATLAS_SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("ATLAS_SPOTIFY_CLIENT_SECRET", raising=False)
    clear_refresh_token()

    command_registry = CommandRegistry()
    plugin_registry = PluginRegistry()
    loader = PluginLoader(command_registry, plugin_registry)

    loader.load_plugin_class(SpotifyPlugin)

    record = plugin_registry.get("spotify")
    assert record is not None
    assert record.status is PluginStatus.DISABLED
    assert "ATLAS_SPOTIFY_CLIENT_ID" in record.reason
    # No Spotify commands should have leaked into the registry.
    assert "spotify_play" not in command_registry


def test_disables_cleanly_with_credentials_but_no_token(monkeypatch):
    monkeypatch.setenv("ATLAS_SPOTIFY_CLIENT_ID", "dummy")
    monkeypatch.setenv("ATLAS_SPOTIFY_CLIENT_SECRET", "dummy")
    clear_refresh_token()

    command_registry = CommandRegistry()
    plugin_registry = PluginRegistry()
    loader = PluginLoader(command_registry, plugin_registry)

    loader.load_plugin_class(SpotifyPlugin)

    record = plugin_registry.get("spotify")
    assert record is not None
    assert record.status is PluginStatus.DISABLED
    assert "spotify-login" in record.reason


def test_loads_when_credentials_and_token_present(monkeypatch):
    monkeypatch.setenv("ATLAS_SPOTIFY_CLIENT_ID", "dummy")
    monkeypatch.setenv("ATLAS_SPOTIFY_CLIENT_SECRET", "dummy")
    save_refresh_token("dummy-token-for-test")
    try:
        command_registry = CommandRegistry()
        plugin_registry = PluginRegistry()
        loader = PluginLoader(command_registry, plugin_registry)

        loader.load_plugin_class(SpotifyPlugin)

        record = plugin_registry.get("spotify")
        assert record is not None
        assert record.status is PluginStatus.LOADED
        assert "spotify_play" in command_registry
    finally:
        clear_refresh_token()
