"""Spotify playback commands (Atlas.md section 27).

"volume up"/"volume down" are deliberately NOT registered here even
though the spec lists them under Spotify too - they're already bound to
system volume (atlas.commands.system_commands), Spotify audio plays
through that anyway, and two grammars bound to the identical phrase would
leave one permanently unreachable. Same reasoning kept "open playlist X"
out - "play playlist X" (below) doesn't collide with anything since it
uses a different verb; "open X" is already the one grammar for
applications and folders (see atlas.commands.application_commands)."""

from __future__ import annotations

from dataclasses import dataclass

from atlas.commands.command import (
    Command,
    CommandCategory,
    CommandContext,
    CommandResult,
    ValidationResult,
)
from atlas.commands.matcher import Grammar
from atlas.commands.parser import CommandParser
from atlas.commands.registry import CommandRegistry
from atlas.integrations.spotify.client import SpotifyApiError, SpotifyClient


def _client(context: CommandContext) -> SpotifyClient:
    return context.extra["spotify_client"]


class PlayCommand(Command):
    name = "spotify_play"
    category = CommandCategory.SPOTIFY

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        try:
            _client(context).play()
        except SpotifyApiError as exc:
            return CommandResult.fail(str(exc))
        return CommandResult.ok("Playing")

    def describe(self) -> str:
        return "Resume Spotify playback"


class PauseCommand(Command):
    name = "spotify_pause"
    category = CommandCategory.SPOTIFY

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        try:
            _client(context).pause()
        except SpotifyApiError as exc:
            return CommandResult.fail(str(exc))
        return CommandResult.ok("Paused")

    def describe(self) -> str:
        return "Pause Spotify playback"


class NextSongCommand(Command):
    name = "spotify_next"
    category = CommandCategory.SPOTIFY

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        try:
            _client(context).next_track()
        except SpotifyApiError as exc:
            return CommandResult.fail(str(exc))
        return CommandResult.ok("Skipped to next song")

    def describe(self) -> str:
        return "Play the next song"


class PreviousSongCommand(Command):
    name = "spotify_previous"
    category = CommandCategory.SPOTIFY

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        try:
            _client(context).previous_track()
        except SpotifyApiError as exc:
            return CommandResult.fail(str(exc))
        return CommandResult.ok("Went back to previous song")

    def describe(self) -> str:
        return "Play the previous song"


@dataclass
class SearchSpotifyCommand(Command):
    query: str
    name = "spotify_search"
    category = CommandCategory.SPOTIFY

    def validate(self) -> ValidationResult:
        if not self.query.strip():
            return ValidationResult.failure("No search query given")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        try:
            track = _client(context).search_track(self.query)
        except SpotifyApiError as exc:
            return CommandResult.fail(str(exc))
        if track is None:
            return CommandResult.fail(f"No results for '{self.query}'")
        artist = track["artists"][0]["name"]
        return CommandResult.ok(f"Found: {track['name']} by {artist}", uri=track["uri"])

    def describe(self) -> str:
        return f"Search Spotify for {self.query}"


@dataclass
class PlayQueryCommand(Command):
    """Covers both "play <song>" and "play <artist>" - Spotify's track
    search matches on artist name too, so a plain track search is a
    reasonable single implementation for both phrasings."""

    query: str
    name = "spotify_play_query"
    category = CommandCategory.SPOTIFY

    def validate(self) -> ValidationResult:
        if not self.query.strip():
            return ValidationResult.failure("No song or artist given")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        client = _client(context)
        try:
            track = client.search_track(self.query)
            if track is None:
                return CommandResult.fail(f"No results for '{self.query}'")
            client.play_uris([track["uri"]])
        except SpotifyApiError as exc:
            return CommandResult.fail(str(exc))
        artist = track["artists"][0]["name"]
        return CommandResult.ok(f"Playing {track['name']} by {artist}")

    def describe(self) -> str:
        return f"Play {self.query}"


@dataclass
class PlayPlaylistCommand(Command):
    playlist: str
    name = "spotify_play_playlist"
    category = CommandCategory.SPOTIFY

    def validate(self) -> ValidationResult:
        if not self.playlist.strip():
            return ValidationResult.failure("No playlist given")
        return ValidationResult.success()

    def execute(self, context: CommandContext) -> CommandResult:
        client = _client(context)
        try:
            playlist = client.find_playlist(self.playlist)
            if playlist is None:
                return CommandResult.fail(f"Playlist '{self.playlist}' was not found")
            client.play_context(playlist["uri"])
        except SpotifyApiError as exc:
            return CommandResult.fail(str(exc))
        return CommandResult.ok(f"Playing playlist {playlist['name']}")

    def describe(self) -> str:
        return f"Play playlist {self.playlist}"


_COMMANDS: tuple[type[Command], ...] = (
    PlayCommand,
    PauseCommand,
    NextSongCommand,
    PreviousSongCommand,
    SearchSpotifyCommand,
    PlayQueryCommand,
    PlayPlaylistCommand,
)


def register(registry: CommandRegistry) -> None:
    for command_cls in _COMMANDS:
        if command_cls.name not in registry:
            registry.register(command_cls)


def _query_builder(groups: dict[str, str]) -> dict[str, str]:
    return {"query": groups["query"].strip()}


def _playlist_builder(groups: dict[str, str]) -> dict[str, str]:
    return {"playlist": groups["playlist"].strip()}


def register_grammars(parser: CommandParser) -> None:
    parser.add_grammar(Grammar("spotify_play", ("play", "resume")))
    parser.add_grammar(Grammar("spotify_pause", ("pause",)))
    parser.add_grammar(Grammar("spotify_next", ("next song",)))
    parser.add_grammar(Grammar("spotify_previous", ("previous song",)))

    # More specific patterns first - "play playlist X" would otherwise be
    # swallowed by the generic "play {query}" catch-all below.
    parser.add_pattern("spotify_play_playlist", "play playlist {playlist}", _playlist_builder)
    parser.add_pattern("spotify_search", "search spotify for {query}", _query_builder)
    parser.add_pattern("spotify_play_query", "play {query}", _query_builder)
