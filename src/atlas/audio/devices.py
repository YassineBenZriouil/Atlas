"""Audio device descriptor (Atlas.md section 7)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioDevice:
    device_id: str
    name: str
    max_input_channels: int
    default_sample_rate: int
