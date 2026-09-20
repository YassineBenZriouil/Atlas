"""Deterministic text normalization. Normalization MUST NOT change semantic meaning."""

from __future__ import annotations

import re

_NUMBER_WORDS: dict[str, str] = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "twenty": "20",
    "thirty": "30",
    "forty": "40",
    "fifty": "50",
    "sixty": "60",
    "seventy": "70",
    "eighty": "80",
    "ninety": "90",
    "hundred": "100",
    "too": "2",
}

_FILLER_WORDS = frozenset({"to", "the"})

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_RE = re.compile(r"[^\w\s]")


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def strip_punctuation(text: str) -> str:
    return _PUNCTUATION_RE.sub("", text)


def words_to_numbers(text: str, *, only_after: tuple[str, ...] = ()) -> str:
    """Replace number words with digits.

    If `only_after` is given, a word is only converted when the nearest
    preceding non-filler token is one of those words - e.g. "monitor two"
    converts, and so does "volume to thirty" (skipping the filler "to" to
    find "volume"), but "go to brave" is untouched since "brave" isn't a
    number word in the first place and "go" is never a trigger.
    """
    tokens = text.split()
    out: list[str] = []
    for i, token in enumerate(tokens):
        replacement = _NUMBER_WORDS.get(token)
        if replacement is None:
            out.append(token)
            continue
        if only_after:
            j = i - 1
            while j >= 0 and tokens[j] in _FILLER_WORDS:
                j -= 1
            if j < 0 or tokens[j] not in only_after:
                out.append(token)
                continue
        out.append(replacement)
    return " ".join(out)


def normalize(text: str) -> str:
    """Normalize a raw speech transcript for deterministic parsing.

    Examples:
        "Monitor two" -> "monitor 2"
        "V S code" -> "vs code"
    """
    text = text.lower().strip()
    text = collapse_whitespace(text)
    text = words_to_numbers(text, only_after=("monitor", "screen", "display", "volume"))
    text = text.replace("v s code", "vs code")
    text = collapse_whitespace(text)
    return text
