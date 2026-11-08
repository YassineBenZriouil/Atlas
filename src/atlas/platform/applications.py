"""Application lookup/lifecycle interface (Atlas.md section 18), plus the
platform-neutral part every backend shares: turning a spoken name into a
configured application (exact alias, then deterministic fuzzy/prefix
matching against configured aliases only - never onto a path)."""

from __future__ import annotations

import difflib
from abc import ABC, abstractmethod
from dataclasses import dataclass

from atlas.config.schema import AtlasConfig
from atlas.platform.windowing import WindowHandle

_FUZZY_ALIAS_CUTOFF = 0.75
_MIN_PREFIX_LENGTH = 3
_MIN_RATIO_LENGTH = 5


@dataclass(frozen=True)
class ApplicationInfo:
    alias: str
    executable_path: str | None


class ApplicationManager(ABC):
    @abstractmethod
    def resolve_alias(self, alias: str) -> ApplicationInfo | None: ...

    @abstractmethod
    def locate(self, alias: str) -> str | None: ...

    @abstractmethod
    def launch(self, alias: str) -> None: ...

    @abstractmethod
    def terminate(self, alias: str) -> None: ...

    @abstractmethod
    def is_running(self, alias: str) -> bool: ...

    @abstractmethod
    def windows_for(self, alias: str) -> list[WindowHandle]: ...


class ApplicationNotFoundError(RuntimeError):
    pass


def resolve_configured_alias(config: AtlasConfig, alias: str) -> ApplicationInfo | None:
    alias_lower = alias.lower().strip()
    for key, entry in config.applications.items():
        if alias_lower == key.lower() or alias_lower in (a.lower() for a in entry.aliases):
            return ApplicationInfo(alias=key, executable_path=entry.executable or None)
    return _resolve_fuzzy(config, alias_lower)


def _resolve_fuzzy(config: AtlasConfig, alias_lower: str) -> ApplicationInfo | None:
    """Deterministic fallback for ASR misrecognitions of an otherwise
    correctly *configured* alias (Atlas.md section 63: fuzzy matching
    is permitted for application names, but must never bypass safety
    validation - this only ever resolves to an alias already present
    in config, never invents a path, and command verbs/dangerous
    command names are matched by exact grammar elsewhere and are
    never reachable through this function at all)."""
    candidates: dict[str, str] = {}
    for key, entry in config.applications.items():
        candidates[key.lower()] = key
        for a in entry.aliases:
            candidates[a.lower()] = key

    # Ratio-based matching against a *short* candidate alias (e.g.
    # "set") is unreliable - a couple of shared characters between two
    # short strings produces a deceptively high ratio ("se" vs "set"
    # is 0.8). Short aliases are handled by the stricter prefix
    # mechanism below instead, which has its own ambiguity guard.
    ratio_candidates = {
        text: key for text, key in candidates.items() if len(text) >= _MIN_RATIO_LENGTH
    }
    match = difflib.get_close_matches(
        alias_lower, ratio_candidates.keys(), n=1, cutoff=_FUZZY_ALIAS_CUTOFF
    )
    if match:
        key = ratio_candidates[match[0]]
        entry = config.applications[key]
        return ApplicationInfo(alias=key, executable_path=entry.executable or None)

    return _resolve_prefix(config, alias_lower, candidates)


def _resolve_prefix(
    config: AtlasConfig, alias_lower: str, candidates: dict[str, str]
) -> ApplicationInfo | None:
    """Short abbreviations ("spot" for "spotify", "disc" for
    "discord", "set" for "settings") often fall below the ratio-based
    cutoff above purely because they're short, even though they're an
    unambiguous truncation. A prefix match either way is still exact,
    deterministic text matching - not a guess - but if the short form
    could mean two different configured apps, ATLAS must not pick one
    (Atlas.md section 28: never guess)."""
    if len(alias_lower) < _MIN_PREFIX_LENGTH:
        return None

    matched_keys = {
        key
        for candidate_text, key in candidates.items()
        if len(candidate_text) >= _MIN_PREFIX_LENGTH
        and (candidate_text.startswith(alias_lower) or alias_lower.startswith(candidate_text))
    }
    if len(matched_keys) != 1:
        return None

    key = next(iter(matched_keys))
    entry = config.applications[key]
    return ApplicationInfo(alias=key, executable_path=entry.executable or None)
