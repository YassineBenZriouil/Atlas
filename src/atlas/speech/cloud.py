"""Cloud speech fallback: any OpenAI-compatible `/audio/transcriptions`
endpoint. Only the post-wake utterance is sent; the API key comes from
the environment and is never logged."""

from __future__ import annotations

import io
import wave

import requests

from atlas.speech.transcriber import Transcriber, TranscriberError

_TIMEOUT_SECONDS = 10.0


def pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return buffer.getvalue()


class CloudTranscriber(Transcriber):
    name = "cloud"

    def __init__(self, url: str, api_key: str, *, model: str, language: str = "") -> None:
        self._url = url
        self._api_key = api_key
        self._model = model
        # Whisper-style APIs take ISO-639-1 ("en"), config uses "en-us".
        self._language = language.split("-")[0]

    def transcribe(self, pcm: bytes, sample_rate: int) -> str:
        data = {"model": self._model}
        if self._language:
            data["language"] = self._language
        try:
            response = requests.post(
                self._url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": ("utterance.wav", pcm_to_wav(pcm, sample_rate), "audio/wav")},
                data=data,
                timeout=_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise TranscriberError(f"cloud request failed: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise TranscriberError(f"cloud returned HTTP {response.status_code}")
        try:
            return str(response.json().get("text", ""))
        except ValueError as exc:
            raise TranscriberError("cloud returned non-JSON response") from exc
