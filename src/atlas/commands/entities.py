"""Deterministic entity extraction helpers (Atlas.md section 10, step 4).

These operate on already-normalized text (see atlas.utils.strings.normalize).
Full grammar-driven entity binding for parameterized commands (move/resize/
volume/etc.) is a Phase 2 concern; these helpers are the building blocks.
"""

from __future__ import annotations

import re

_MONITOR_RE = re.compile(r"\bmonitor (\d+)\b")
_VOLUME_RE = re.compile(r"\bvolume(?: to)? (\d+)\b")
_DIMENSIONS_RE = re.compile(r"\b(\d+)\s*by\s*(\d+)\b")


def extract_monitor_number(normalized_text: str) -> int | None:
    match = _MONITOR_RE.search(normalized_text)
    return int(match.group(1)) if match else None


def extract_volume_level(normalized_text: str) -> int | None:
    match = _VOLUME_RE.search(normalized_text)
    if not match:
        return None
    return max(0, min(100, int(match.group(1))))


def extract_dimensions(normalized_text: str) -> tuple[int, int] | None:
    match = _DIMENSIONS_RE.search(normalized_text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))
