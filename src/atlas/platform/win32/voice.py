"""Windows voice loop (`[speech] engine = "windows"`), all on-device, no
model download.

- Wake word: Windows.Media.SpeechRecognition with a one-word list grammar.
- Command: the same recognizer constrained to ATLAS's whole command
  vocabulary (atlas.speech.vocabulary - Atlas.md section 9, Mode B). The
  utterance is recorded at the same time; if the grammar can't match it
  (free-text commands like "search the web for ..."), that recording goes
  to the next layers in `[speech] providers` (cloud, ...).

History: free dictation for commands was tried twice and dropped - WinRT
online dictation returned Status=Unknown with no text on every utterance,
and SAPI offline dictation turned "open brave" into "Open daily for"."""

from __future__ import annotations

import asyncio
import dataclasses
import threading

from atlas.application.app import Application
from atlas.application.voice_loop import EventCallback, VoiceUnavailableError, strip_wake_phrase
from atlas.audio.utterance import record_utterance
from atlas.logging_setup import get_logger
from atlas.speech.transcriber import TranscriberChain, create_transcriber_chain
from atlas.speech.vocabulary import command_vocabulary

logger = get_logger("windows_voice")

_ACCESS_DENIED = 0x80070005
_MIC_DENIED_MESSAGE = (
    "Windows blocked microphone access - allow it in Settings > Privacy & security > "
    'Microphone ("Let desktop apps access your microphone")'
)


def _describe_os_error(exc: OSError) -> str:
    code = (exc.winerror or 0) & 0xFFFFFFFF if hasattr(exc, "winerror") else 0
    if code == _ACCESS_DENIED:
        return _MIC_DENIED_MESSAGE
    return f"Windows speech error: {exc}"


class WindowsVoiceLoop:
    def __init__(
        self,
        app: Application,
        *,
        wake_phrase: str = "atlas",
        listen_timeout_seconds: float = 8.0,
        device_id: str = "default",
        sample_rate: int = 16000,
        transcribers: TranscriberChain | None = None,
        on_event: EventCallback | None = None,
    ) -> None:
        self._app = app
        self._wake_phrase = wake_phrase.lower().strip()
        self._listen_timeout = listen_timeout_seconds
        self._device_id = device_id
        self._sample_rate = sample_rate
        self._transcribers = transcribers
        self._on_event = on_event or (lambda kind, message: None)
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[None] | None = None
        self._ready = threading.Event()
        self._start_error: str = ""
        self._vocabulary: list[str] = []

    def start(self) -> None:
        config = self._app.config
        assert config is not None and self._app.parser is not None
        self._vocabulary = command_vocabulary(self._app.parser, config)
        if self._transcribers is None:
            # Layers after the command grammar. "native" is that grammar itself here:
            # SAPI free dictation is too inaccurate to run commands from.
            fallback = [p for p in config.speech.providers if p != "native"]
            self._transcribers = create_transcriber_chain(
                dataclasses.replace(config.speech, providers=fallback)
            )
        self._thread = threading.Thread(target=self._run, name="windows-voice", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=15)
        if self._start_error:
            self._thread.join(timeout=5)
            raise VoiceUnavailableError(self._start_error)
        logger.info("Windows voice loop started (wake phrase: %s)", self._wake_phrase)

    def stop(self) -> None:
        if self._loop is not None and self._task is not None:
            self._loop.call_soon_threadsafe(self._task.cancel)
        if self._thread is not None:
            self._thread.join(timeout=10)
        logger.info("Windows voice loop stopped")

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        try:
            self._task = self._loop.create_task(self._main())
            self._loop.run_until_complete(self._task)
        except asyncio.CancelledError:
            pass
        finally:
            self._ready.set()
            self._loop.close()

    async def _main(self) -> None:
        try:
            wake = await self._build_recognizer([self._wake_phrase], "wake")
            command = await self._build_recognizer(self._vocabulary, "commands")
        except OSError as exc:
            self._start_error = _describe_os_error(exc)
            return
        self._ready.set()
        try:
            while True:
                self._on_event("status", "sleeping")
                if not await self._heard_wake_word(wake):
                    continue
                self._on_event("wake", "Wake word detected")
                self._on_event("status", "listening")
                await self._handle_command(command)
        except OSError as exc:
            # The loop can't keep going (mic unplugged, access revoked...).
            message = _describe_os_error(exc)
            logger.error("Windows voice loop stopped: %s", message)
            self._on_event("voice_lost", message)
        finally:
            wake.close()
            command.close()

    async def _build_recognizer(self, phrases: list[str], tag: str):  # type: ignore[no-untyped-def]
        import datetime

        from winrt.windows.media.speechrecognition import (
            SpeechRecognitionListConstraint,
            SpeechRecognitionResultStatus,
            SpeechRecognizer,
        )

        recognizer = SpeechRecognizer()
        recognizer.constraints.append(SpeechRecognitionListConstraint(phrases, tag))
        recognizer.timeouts.initial_silence_timeout = datetime.timedelta(
            seconds=self._listen_timeout
        )
        result = await recognizer.compile_constraints_async()
        if result.status != SpeechRecognitionResultStatus.SUCCESS:
            raise OSError(f"could not compile the {tag} grammar ({result.status.name})")
        return recognizer

    async def _heard_wake_word(self, wake) -> bool:  # type: ignore[no-untyped-def]
        from winrt.windows.media.speechrecognition import (
            SpeechRecognitionConfidence,
            SpeechRecognitionResultStatus,
        )

        result = await wake.recognize_async()
        return (
            result.status == SpeechRecognitionResultStatus.SUCCESS
            and result.confidence != SpeechRecognitionConfidence.REJECTED
            and result.text.lower().strip(" .!?,") == self._wake_phrase
        )

    async def _handle_command(self, command) -> None:  # type: ignore[no-untyped-def]
        from winrt.windows.media.speechrecognition import (
            SpeechRecognitionConfidence,
            SpeechRecognitionResultStatus,
        )

        stop_recording = threading.Event()
        recording = asyncio.ensure_future(
            asyncio.to_thread(
                record_utterance,
                self._device_id,
                self._sample_rate,
                start_timeout=self._listen_timeout,
                stop=stop_recording,
            )
        )
        result = await command.recognize_async()
        matched = (
            result.status == SpeechRecognitionResultStatus.SUCCESS
            and result.confidence != SpeechRecognitionConfidence.REJECTED
            and bool(result.text)
        )
        if matched:
            stop_recording.set()
        pcm = await recording
        logger.info(
            "Command grammar: status=%s confidence=%s text=%r; recorded %.1fs",
            result.status.name,
            result.confidence.name,
            result.text,
            len(pcm) / 2 / self._sample_rate,
        )
        await self._act(result.text if matched else "", "windows", pcm)

    async def _act(self, text: str, provider: str, pcm: bytes) -> None:
        """Run a grammar match, or fall back to the other layers on the recording."""
        assert self._transcribers is not None
        if not text and pcm and self._transcribers.transcribers:
            self._on_event("status", "recognizing")
            text, provider = await asyncio.to_thread(
                self._transcribers.transcribe, pcm, self._sample_rate, ""
            )
            logger.info("Fallback recognition via %s: %r", provider, text)
        text = strip_wake_phrase(text, self._wake_phrase).strip(" .!?")
        if not text:
            self._on_event(
                "timeout",
                "Didn't catch a command I know"
                if pcm
                else f'Heard "{self._wake_phrase.title()}" but no command after it',
            )
            return
        self._on_event("engine", provider)
        self._on_event("heard", text)
        self._on_event("status", "processing")
        outcome = await asyncio.to_thread(self._app.run_text_command, text)
        self._on_event("result" if outcome.success else "failed", outcome.message)
