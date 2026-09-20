"""The command parser (Atlas.md section 10). NEVER executes arbitrary text -
only text matching a registered grammar can produce a Command instance."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from atlas.commands.command import Command
from atlas.commands.matcher import Grammar, PatternGrammar, compile_pattern, match_exact
from atlas.commands.registry import CommandRegistry
from atlas.utils.strings import normalize

ParamBuilder = Callable[[dict[str, str]], dict[str, Any]]


@dataclass(frozen=True)
class NeedsClarification:
    """Atlas.md sections 28-29: insufficient information to build a command,
    but a known verb/target - so ATLAS asks one specific question instead of
    either guessing or giving up. `resolve` interprets exactly one follow-up
    utterance as the missing piece; returning None means it still couldn't
    be resolved and the clarification is abandoned."""

    command_name: str
    prompt: str
    resolve: Callable[[str], Command | None]


CustomMatcher = Callable[[str], "Command | NeedsClarification | None"]


@dataclass(frozen=True)
class ParseResult:
    command: Command | None
    raw_text: str
    normalized_text: str
    matched_name: str | None
    error: str | None = None
    clarification: NeedsClarification | None = None

    @property
    def ok(self) -> bool:
        return self.command is not None

    @property
    def needs_clarification(self) -> bool:
        return self.clarification is not None


class CommandParser:
    """Three layers, tried in order: exact phrases (no entities), templated
    patterns (entities, resolved to raw strings - alias/path resolution
    happens later in a command's execute(), not here), then custom matchers
    for anything a template can't express (currently just the bare-"move X"
    clarification)."""

    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry
        self._grammars: list[Grammar] = []
        self._pattern_grammars: list[tuple[PatternGrammar, ParamBuilder]] = []
        self._custom_matchers: list[CustomMatcher] = []

    def add_grammar(self, grammar: Grammar) -> None:
        self._grammars.append(grammar)

    def add_pattern(
        self,
        command_name: str,
        template: str,
        param_builder: ParamBuilder = lambda groups: dict(groups),
    ) -> None:
        self._pattern_grammars.append((compile_pattern(command_name, template), param_builder))

    def add_custom_matcher(self, matcher: CustomMatcher) -> None:
        self._custom_matchers.append(matcher)

    def _build(
        self, command_name: str, raw_text: str, normalized: str, **kwargs: Any
    ) -> ParseResult:
        command_cls = self._registry.get(command_name)
        if command_cls is None:
            return ParseResult(
                command=None,
                raw_text=raw_text,
                normalized_text=normalized,
                matched_name=command_name,
                error=f"Matched grammar '{command_name}' has no registered command.",
            )
        return ParseResult(
            command=command_cls(**kwargs),
            raw_text=raw_text,
            normalized_text=normalized,
            matched_name=command_name,
        )

    def parse(self, raw_text: str) -> ParseResult:
        normalized = normalize(raw_text)

        matched_name = match_exact(normalized, self._grammars)
        if matched_name is not None:
            return self._build(matched_name, raw_text, normalized)

        for grammar, builder in self._pattern_grammars:
            match = grammar.pattern.match(normalized)
            if match is None:
                continue
            try:
                kwargs = builder(match.groupdict())
            except ValueError as exc:
                return ParseResult(
                    command=None,
                    raw_text=raw_text,
                    normalized_text=normalized,
                    matched_name=grammar.command_name,
                    error=str(exc),
                )
            return self._build(grammar.command_name, raw_text, normalized, **kwargs)

        for matcher in self._custom_matchers:
            outcome = matcher(normalized)
            if isinstance(outcome, NeedsClarification):
                return ParseResult(
                    command=None,
                    raw_text=raw_text,
                    normalized_text=normalized,
                    matched_name=outcome.command_name,
                    clarification=outcome,
                )
            if outcome is not None:
                return ParseResult(
                    command=outcome,
                    raw_text=raw_text,
                    normalized_text=normalized,
                    matched_name=outcome.name,
                )

        return ParseResult(
            command=None,
            raw_text=raw_text,
            normalized_text=normalized,
            matched_name=None,
            error="I didn't understand that command.",
        )
