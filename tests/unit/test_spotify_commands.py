from unittest.mock import MagicMock

from atlas.commands.command import CommandContext
from atlas.commands.parser import CommandParser
from atlas.commands.registry import CommandRegistry
from atlas.integrations.spotify.client import SpotifyApiError
from atlas.integrations.spotify.commands import (
    NextSongCommand,
    PauseCommand,
    PlayCommand,
    PlayPlaylistCommand,
    PlayQueryCommand,
    PreviousSongCommand,
    SearchSpotifyCommand,
    register,
    register_grammars,
)


def make_context(client=None) -> CommandContext:
    return CommandContext(extra={"spotify_client": client or MagicMock()})


def test_play_calls_client():
    client = MagicMock()
    result = PlayCommand().execute(make_context(client))
    assert result.success
    client.play.assert_called_once()


def test_pause_calls_client():
    client = MagicMock()
    result = PauseCommand().execute(make_context(client))
    assert result.success
    client.pause.assert_called_once()


def test_next_and_previous():
    client = MagicMock()
    NextSongCommand().execute(make_context(client))
    PreviousSongCommand().execute(make_context(client))
    client.next_track.assert_called_once()
    client.previous_track.assert_called_once()


def test_api_error_becomes_clean_failure():
    client = MagicMock()
    client.play.side_effect = SpotifyApiError("boom")
    result = PlayCommand().execute(make_context(client))
    assert not result.success
    assert "boom" in result.message


def test_search_returns_track_info():
    client = MagicMock()
    client.search_track.return_value = {
        "name": "Song",
        "artists": [{"name": "Artist"}],
        "uri": "spotify:track:1",
    }
    result = SearchSpotifyCommand(query="song").execute(make_context(client))
    assert result.success
    assert "Song" in result.message
    assert "Artist" in result.message


def test_search_no_results():
    client = MagicMock()
    client.search_track.return_value = None
    result = SearchSpotifyCommand(query="nonexistent").execute(make_context(client))
    assert not result.success


def test_play_query_plays_first_match():
    client = MagicMock()
    client.search_track.return_value = {
        "name": "Song",
        "artists": [{"name": "Artist"}],
        "uri": "spotify:track:1",
    }
    result = PlayQueryCommand(query="song").execute(make_context(client))
    assert result.success
    client.play_uris.assert_called_once_with(["spotify:track:1"])


def test_play_playlist_not_found():
    client = MagicMock()
    client.find_playlist.return_value = None
    result = PlayPlaylistCommand(playlist="nonexistent").execute(make_context(client))
    assert not result.success


def test_play_playlist_found_plays_context():
    client = MagicMock()
    client.find_playlist.return_value = {"name": "Workout", "uri": "spotify:playlist:1"}
    result = PlayPlaylistCommand(playlist="workout").execute(make_context(client))
    assert result.success
    client.play_context.assert_called_once_with("spotify:playlist:1")


def test_grammar_ordering_play_playlist_before_generic_play():
    registry = CommandRegistry()
    register(registry)
    parser = CommandParser(registry)
    register_grammars(parser)

    result = parser.parse("play playlist workout")

    assert result.ok
    assert isinstance(result.command, PlayPlaylistCommand)
    assert result.command.playlist == "workout"


def test_bare_play_resumes_rather_than_query():
    registry = CommandRegistry()
    register(registry)
    parser = CommandParser(registry)
    register_grammars(parser)

    result = parser.parse("play")

    assert result.ok
    assert isinstance(result.command, PlayCommand)
