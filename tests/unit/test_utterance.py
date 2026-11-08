import numpy as np

from atlas.audio.utterance import capture_utterance, rms


def block(level: int, n: int = 1600) -> bytes:
    return (np.ones(n, dtype=np.int16) * level).tobytes()


def feed(levels):
    blocks = iter([block(level) for level in levels])
    return lambda: next(blocks)


def test_rms():
    assert rms(block(1000)) == 1000
    assert rms(b"") == 0


def test_captures_speech_then_stops_after_trailing_silence():
    levels = [50, 50, 50, 50, 3000, 3000, 3000] + [50] * 8 + [3000] * 50
    pcm = capture_utterance(feed(levels), block_seconds=0.1, start_timeout=5)
    assert len(pcm) == len(block(0)) * 15  # stopped 0.8 s after speech; never read the rest


def test_speaking_straight_after_wake_is_still_caught():
    levels = [3000] * 10 + [50] * 8
    assert capture_utterance(feed(levels), block_seconds=0.1, start_timeout=5)


def test_no_speech_before_timeout_returns_empty():
    pcm = capture_utterance(feed([50] * 100), block_seconds=0.1, start_timeout=1.0)
    assert pcm == b""


def test_steady_background_noise_is_not_speech():
    # A constant hum raises the threshold above itself.
    pcm = capture_utterance(feed([450] * 100), block_seconds=0.1, start_timeout=2.0)
    assert pcm == b""


def test_speech_above_noise_floor_is_caught_in_a_noisy_room():
    levels = [450, 450, 450, 5000, 5000] + [450] * 9
    pcm = capture_utterance(feed(levels), block_seconds=0.1, start_timeout=5)
    assert pcm


def test_never_runs_past_max_seconds():
    pcm = capture_utterance(feed([3000] * 200), block_seconds=0.1, start_timeout=5, max_seconds=2)
    assert len(pcm) == len(block(0)) * 20


def test_stop_event_ends_recording_early():
    import threading

    stop = threading.Event()
    reads = 0

    def read():
        nonlocal reads
        reads += 1
        if reads == 6:
            stop.set()
        return block(3000)

    capture_utterance(read, block_seconds=0.1, start_timeout=5, stop=stop)
    assert reads == 6
