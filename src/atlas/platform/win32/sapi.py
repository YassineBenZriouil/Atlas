"""Windows-native speech recognition: SAPI's in-process dictation
recognizer, fed an in-memory PCM buffer (audio never touches disk)."""

from __future__ import annotations

import time

import pythoncom
import win32com.client

from atlas.speech.transcriber import Transcriber, TranscriberError

_SAFT_16KHZ_16BIT_MONO = 18
_TIMEOUT_SECONDS = 10.0
_RPC_E_CHANGED_MODE = -2147417850
# Trailing silence lets dictation finalize the last phrase before the stream ends.
_TAIL_SILENCE = b"\x00\x00" * 8000


class SapiTranscriber(Transcriber):
    name = "native"

    def transcribe(self, pcm: bytes, sample_rate: int) -> str:
        if sample_rate != 16000:
            raise TranscriberError(f"SAPI path expects 16 kHz audio, got {sample_rate}")
        try:
            # Called from the audio callback thread; COM must be initialized per thread.
            # RPC_E_CHANGED_MODE just means the thread is already in an apartment.
            try:
                pythoncom.CoInitialize()
            except pythoncom.com_error as exc:
                if exc.hresult != _RPC_E_CHANGED_MODE:
                    raise
            return self._recognize(pcm)
        except pythoncom.com_error as exc:
            raise TranscriberError(f"SAPI error: {exc}") from exc

    def _recognize(self, pcm: bytes) -> str:
        phrases: list[str] = []
        done: list[bool] = []

        class Events:
            def OnRecognition(self, stream_number, position, recognition_type, result):  # noqa: N802
                phrases.append(win32com.client.Dispatch(result).PhraseInfo.GetText())

            def OnEndStream(self, *args):  # noqa: N802
                done.append(True)

        recognizer = win32com.client.Dispatch("SAPI.SpInprocRecognizer")
        if recognizer.GetRecognizers().Count == 0:
            raise TranscriberError("No SAPI recognizer installed")
        audio_format = win32com.client.Dispatch("SAPI.SpAudioFormat")
        audio_format.Type = _SAFT_16KHZ_16BIT_MONO
        stream = win32com.client.Dispatch("SAPI.SpMemoryStream")
        stream.Format = audio_format
        stream.SetData(pcm + _TAIL_SILENCE)
        stream.Seek(0)
        recognizer.AudioInputStream = stream

        context = win32com.client.DispatchWithEvents(recognizer.CreateRecoContext(), Events)
        grammar = context.CreateGrammar()
        grammar.DictationLoad()
        grammar.DictationSetState(1)

        deadline = time.monotonic() + _TIMEOUT_SECONDS
        while not done:
            if time.monotonic() > deadline:
                raise TranscriberError("SAPI timed out")
            pythoncom.PumpWaitingMessages()
            time.sleep(0.01)
        return " ".join(phrases)
