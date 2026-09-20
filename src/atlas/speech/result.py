"""Normalized output of a speech engine (Atlas.md section 6)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecognitionResult:
    text: str
    confidence: float
    is_final: bool
