"""Post-wake utterance transcription chain (docs/ROADMAP.md, Phase 1).

VoiceLoop buffers an utterance's PCM while Vosk endpoints it live, then
hands the buffer here. Providers are tried in configured order; the first
non-empty transcript wins. Vosk's live result is the implicit last
fallback, so a failing provider can never lose the utterance."""

from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod

from atlas.config.schema import SpeechConfig
from atlas.logging_setup import get_logger

logger = get_logger("speech")

LOCAL_PROVIDER = "vosk"


class TranscriberError(RuntimeError):
    pass


class Transcriber(ABC):
    name: str

    @abstractmethod
    def transcribe(self, pcm: bytes, sample_rate: int) -> str:
        """16-bit mono PCM in, transcript out. Raises TranscriberError."""
        ...


class TranscriberChain:
    def __init__(self, transcribers: list[Transcriber]) -> None:
        self.transcribers = transcribers

    def transcribe(self, pcm: bytes, sample_rate: int, local_text: str) -> tuple[str, str]:
        """Returns (text, provider name)."""
        for transcriber in self.transcribers:
            try:
                text = transcriber.transcribe(pcm, sample_rate).strip()
            except TranscriberError as exc:
                logger.warning("Speech provider %s failed, falling back: %s", transcriber.name, exc)
                continue
            if text:
                return text, transcriber.name
            logger.info("Speech provider %s heard nothing, falling back", transcriber.name)
        return local_text, LOCAL_PROVIDER


def create_transcriber_chain(config: SpeechConfig) -> TranscriberChain:
    transcribers: list[Transcriber] = []
    for name in config.providers:
        if name == "native":
            from atlas.platform import get_backend

            native = get_backend().native_transcriber
            if native is not None:
                transcribers.append(native())
            else:
                logger.info("No native speech recognizer on %s yet; skipping", sys.platform)
        elif name == "cloud":
            from dotenv import load_dotenv

            from atlas.speech.cloud import CloudTranscriber

            load_dotenv()
            api_key = os.environ.get("ATLAS_STT_API_KEY", "")
            if not api_key:
                logger.info("Cloud speech skipped: ATLAS_STT_API_KEY not set (see .env.example)")
                continue
            transcribers.append(
                CloudTranscriber(
                    config.cloud_url, api_key, model=config.cloud_model, language=config.language
                )
            )
        elif name != LOCAL_PROVIDER:
            logger.warning("Unknown speech provider %r in config; ignoring", name)
    logger.info(
        "Speech providers: %s",
        " -> ".join([t.name for t in transcribers] + [LOCAL_PROVIDER]),
    )
    return TranscriberChain(transcribers)
