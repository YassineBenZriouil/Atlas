"""Deterministic phrase matching. No fuzzy/semantic guessing at this layer -
see Atlas.md section 63 for where fuzzy matching is and is not permitted."""

from __future__ import annotations

import re
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


@dataclass(frozen=True)
class PatternGrammar:
    """A template like "open {application}" or "resize {application} to
    {width} by {height}" compiled to an anchored regex with one named group
    per `{placeholder}`. Still deterministic template matching, not free-form
    parsing - every placeholder must be declared up front."""

    command_name: str
    pattern: re.Pattern[str]
    param_names: tuple[str, ...]


def compile_pattern(command_name: str, template: str) -> PatternGrammar:
    param_names = tuple(re.findall(r"\{(\w+)\}", template))
    parts = re.split(r"(\{\w+\})", template)
    regex_parts: list[str] = []
    for part in parts:
        match = re.fullmatch(r"\{(\w+)\}", part)
        if match:
            regex_parts.append(rf"(?P<{match.group(1)}>.+?)")
        else:
            regex_parts.append(re.escape(part))
    pattern = re.compile("^" + "".join(regex_parts) + "$")
    return PatternGrammar(command_name, pattern, param_names)


def match_pattern(
    normalized_text: str, grammars: list[PatternGrammar]
) -> tuple[str, dict[str, str]] | None:
    for grammar in grammars:
        match = grammar.pattern.match(normalized_text)
        if match:
            return grammar.command_name, match.groupdict()
    return None
