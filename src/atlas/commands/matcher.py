"""Deterministic phrase matching. No fuzzy/semantic guessing at this layer -
see Atlas.md section 63 for where fuzzy matching is and is not permitted."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Grammar:
    """Maps a set of exact, already-normalized phrases to one command name."""

    command_name: str
    phrases: tuple[str, ...]


def match_exact(normalized_text: str, grammars: list[Grammar]) -> str | None:
    for grammar in grammars:
        if normalized_text in grammar.phrases:
            return grammar.command_name
    return None
