"""Everything ATLAS can be told, as a list of phrases for a constrained
recognizer (Atlas.md section 9, Mode B: "recognize the available command
vocabulary... avoid unrestricted dictation"). Built from the live parser and
config, so new commands, apps and aliases are recognizable automatically.

Templates with free-text slots ({query}, {playlist}, {width}...) can't be
listed; those commands go through the free-dictation layers instead."""

from __future__ import annotations

import itertools
import re

from atlas.commands.parser import CommandParser
from atlas.config.schema import AtlasConfig
from atlas.platform.keyboard import SPECIAL_KEYS

_MONITOR_WORDS = ("one", "two", "three", "four")
_VOLUME_WORDS = (
    "zero",
    "ten",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
)
_KNOWN_FOLDERS = ("downloads", "documents", "desktop", "pictures")
_MODIFIERS = ("control", "alt", "shift", "windows")
# Answers to "Say 'confirm' to proceed" and "Which monitor?".
_FOLLOW_UPS = (
    "confirm",
    "yes",
    "confirmed",
    "do it",
    "no",
    "cancel",
    *_MONITOR_WORDS,
    *(f"monitor {w}" for w in _MONITOR_WORDS),
    *(f"screen {w}" for w in _MONITOR_WORDS),
)


def _key_phrases() -> list[str]:
    letters = [chr(c) for c in range(ord("a"), ord("z") + 1)]
    keys = [*sorted(SPECIAL_KEYS), *letters, *(f"f{n}" for n in range(1, 13))]
    return keys + [f"{mod} {key}" for mod in _MODIFIERS for key in letters]


def command_vocabulary(parser: CommandParser, config: AtlasConfig) -> list[str]:
    names = set(config.applications)
    for entry in config.applications.values():
        names.update(alias.lower() for alias in entry.aliases)
    names.update(config.folders)
    names.update(_KNOWN_FOLDERS)
    domains = {
        "application": sorted(n for n in names if n),
        "monitor": list(_MONITOR_WORDS),
        "level": list(_VOLUME_WORDS),
        "keys": _key_phrases(),
    }

    phrases = set(parser.exact_phrases()) | set(_FOLLOW_UPS)
    phrases.update(f"move {name}" for name in domains["application"])  # -> "Which monitor?"
    for template in parser.pattern_templates():
        slots = re.findall(r"\{(\w+)\}", template)
        if not all(slot in domains for slot in slots):
            continue  # free-text slot
        for values in itertools.product(*(domains[slot] for slot in slots)):
            phrase = template
            for slot, value in zip(slots, values, strict=True):
                phrase = phrase.replace(f"{{{slot}}}", value, 1)
            phrases.add(phrase)
    return sorted(phrases)
