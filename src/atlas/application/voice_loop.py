"""Ties microphone capture, wake detection, and speech recognition into the
continuous pipeline described in Atlas.md section 6, feeding recognized
text into Application.run_text_command - the same entry point the
developer console and tests use.

This runs on a background thread. UI code (tray, CLI) should not touch Qt
or print directly from `on_event` if called from the audio callback thread
- marshal to the UI thread first."""

from __future__ import annotations

import threading
from collections.abc import Callable

from atlas.application.app import Application
from atlas.audio.audio_stream import SoundDeviceAudioStream
from atlas.audio.microphone import SoundDeviceMicrophone
from atlas.logging_setup import get_logger
from atlas.speech.engine import SpeechMode
from atlas.speech.vosk_engine import VoskSpeechEngine
from atlas.wake.detector import VoskWakeDetector

logger = get_logger("voice_loop")

EventCallback = Callable[[str, str], None]


class VoiceLoop:
    def __init__(
        self,
        app: Application,
        *,
        model_path: str,
        device_id: str = "default",
        sample_rate: int = 16000,
        blocksize: int = 8000,
        wake_phrase: str = "atlas",
        listen_timeout_seconds: float = 8.0,
        on_event: EventCallback | None = None,
    ) -> None:
        self._app = app
        self._model_path = model_path
        self._sample_rate = sample_rate
        self._wake_phrase = wake_phrase
        self._listen_timeout_seconds = listen_timeout_seconds
        self._frame_seconds = blocksize / sample_rate
        self._on_event = on_event or (lambda kind, message: None)

        self._microphone = SoundDeviceMicrophone(sample_rate=sample_rate, channels=1)
        self._microphone.open(device_id)
        self._stream = SoundDeviceAudioStream(self._microphone, blocksize=blocksize)

        self._wake_detector = VoskWakeDetector(
            model_path, wake_phrase=wake_phrase, sample_rate=sample_rate
        )
        self._speech_engine = VoskSpeechEngine(model_path, sample_rate=sample_rate)

        self._lock = threading.Lock()
        self._listening_for_command = False
        self._frames_since_wake = 0
        self._running = False

    def start(self) -> None:
        self._wake_detector.start()
        self._speech_engine.start()
        self._speech_engine.set_mode(SpeechMode.COMMAND)
        self._running = True
        self._on_event("status", "sleeping")
        self._stream.start(self._on_frame)
        logger.info("Voice loop started (wake phrase: %s)", self._wake_phrase)

    def stop(self) -> None:
        self._running = False
        self._stream.stop()
        self._wake_detector.stop()
        self._speech_engine.stop()
        logger.info("Voice loop stopped")

    def _on_frame(self, frame: bytes) -> None:
        if not self._running:
            return
        with self._lock:
            if not self._listening_for_command:
                if self._wake_detector.process_audio(frame):
                    self._enter_command_mode()
            else:
                self._process_command_frame(frame)

    def _enter_command_mode(self) -> None:
        self._listening_for_command = True
        self._frames_since_wake = 0
        self._on_event("wake", "Wake word detected")
        self._on_event("status", "listening")

    def _process_command_frame(self, frame: bytes) -> None:
        result = self._speech_engine.process_audio(frame)
        if result is not None and result.is_final and result.text:
            self._finish_utterance(result.text)
            return

        self._frames_since_wake += 1
        elapsed = self._frames_since_wake * self._frame_seconds
        if elapsed >= self._listen_timeout_seconds:
            final = self._speech_engine.finalize()
            if final is not None and final.text:
                self._finish_utterance(final.text)
            else:
                self._on_event("timeout", "No command heard")
                self._reset_to_wake()

    def _finish_utterance(self, text: str) -> None:
        self._on_event("heard", text)
        self._on_event("status", "processing")
        result = self._app.run_text_command(text)
        self._on_event("result", result.message)
        self._reset_to_wake()

    def _reset_to_wake(self) -> None:
        self._listening_for_command = False
        self._frames_since_wake = 0
        self._wake_detector.stop()
        self._wake_detector.start()
        self._on_event("status", "sleeping")
