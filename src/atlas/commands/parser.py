"""The command parser (Atlas.md section 10). NEVER executes arbitrary text -
only text matching a registered grammar can produce a Command instance."""

from __future__ import annotations

from dataclasses import dataclass

from atlas.commands.command import Command
from atlas.commands.matcher import Grammar, match_exact
from atlas.commands.registry import CommandRegistry
from atlas.utils.strings import normalize


@dataclass(frozen=True)
class ParseResult:
    command: Command | None
    raw_text: str
    normalized_text: str
    matched_name: str | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.command is not None


class CommandParser:
    """Phase 1 wires exact-phrase grammars only (enough to prove the pipeline
    end-to-end for the developer commands). Alias expansion, fuzzy matching,
    and entity-bound grammars (e.g. "move X to monitor N") arrive in Phase 2.
    """

    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry
        self._grammars: list[Grammar] = []

    def add_grammar(self, grammar: Grammar) -> None:
        self._grammars.append(grammar)

    def parse(self, raw_text: str) -> ParseResult:
        normalized = normalize(raw_text)
        matched_name = match_exact(normalized, self._grammars)
        if matched_name is None:
            return ParseResult(
                command=None,
                raw_text=raw_text,
                normalized_text=normalized,
                matched_name=None,
                error="I didn't understand that command.",
            )

        command_cls = self._registry.get(matched_name)
        if command_cls is None:
            return ParseResult(
                command=None,
                raw_text=raw_text,
                normalized_text=normalized,
                matched_name=matched_name,
                error=f"Matched grammar '{matched_name}' has no registered command.",
            )

        return ParseResult(
            command=command_cls(),
            raw_text=raw_text,
            normalized_text=normalized,
            matched_name=matched_name,
        )
