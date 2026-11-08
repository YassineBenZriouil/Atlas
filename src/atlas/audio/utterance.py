"""Record one spoken command: from now until the speaker goes quiet.

Energy-based endpointing with a noise floor measured from the first blocks,
so a quiet USB mic and a noisy laptop mic both work."""

from __future__ import annotations

import threading
from collections.abc import Callable

import numpy as np

_NOISE_BLOCKS = 3  # first ~0.3 s set the noise floor
_MIN_THRESHOLD = 250.0  # int16 RMS; below this is never treated as speech
_NOISE_MULTIPLIER = 3.0
_MAX_NOISE_FLOOR = 500.0  # so the threshold never exceeds 1500 (normal speech)


def rms(block: bytes) -> float:
    samples = np.frombuffer(block, dtype=np.int16).astype(np.float64)
    return float(np.sqrt(np.mean(samples**2))) if samples.size else 0.0


def capture_utterance(
    read_block: Callable[[], bytes],
    *,
    block_seconds: float,
    start_timeout: float,
    end_silence: float = 0.8,
    max_seconds: float = 10.0,
    stop: threading.Event | None = None,
) -> bytes:
    """Reads 16-bit mono blocks until speech has started and then stayed
    quiet for `end_silence` seconds. Returns the PCM, or b"" if no speech
    started within `start_timeout`."""
    # Whole-block counts: summing 0.1 s floats drifts (8 x 0.1 < 0.8).
    max_blocks = round(max_seconds / block_seconds)
    start_blocks = round(start_timeout / block_seconds)
    end_blocks = round(end_silence / block_seconds)
    blocks: list[bytes] = []
    calibration: list[float] = []
    threshold = _MIN_THRESHOLD
    started = False
    quiet = 0
    while len(blocks) < max_blocks and not (stop and stop.is_set()):
        block = read_block()
        blocks.append(block)
        level = rms(block)
        if len(calibration) < _NOISE_BLOCKS:
            # Measure the room before judging speech; cap it so talking straight
            # away can't push the threshold out of reach.
            calibration.append(level)
            floor = min(min(calibration), _MAX_NOISE_FLOOR)
            threshold = max(_MIN_THRESHOLD, floor * _NOISE_MULTIPLIER)
            continue
        if level >= threshold:
            started = True
            quiet = 0
        elif started:
            quiet += 1
            if quiet >= end_blocks:
                break
        elif len(blocks) >= start_blocks:
            return b""
    return b"".join(blocks) if started else b""


def record_utterance(
    device_id: str,
    sample_rate: int,
    *,
    start_timeout: float,
    block_seconds: float = 0.1,
    stop: threading.Event | None = None,
) -> bytes:
    import sounddevice as sd

    blocksize = int(sample_rate * block_seconds)
    device = None if device_id == "default" else int(device_id)
    with sd.RawInputStream(
        samplerate=sample_rate, channels=1, dtype="int16", blocksize=blocksize, device=device
    ) as stream:
        return capture_utterance(
            lambda: bytes(stream.read(blocksize)[0]),
            block_seconds=block_seconds,
            start_timeout=start_timeout,
            stop=stop,
        )
