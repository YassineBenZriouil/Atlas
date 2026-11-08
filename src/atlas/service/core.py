"""The long-lived ATLAS core (docs/ROADMAP.md, Phase 2): owns the
Application, the voice loop and the event history. The HTTP server and
any UI are just clients of this object."""

from __future__ import annotations

import dataclasses
import os
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

import sounddevice

from atlas import __version__
from atlas.application.app import Application
from atlas.application.voice_loop import Voice, VoiceUnavailableError, create_voice
from atlas.config.loader import config_from_dict, save_config
from atlas.logging_setup import get_logger
from atlas.service.events import EventBus
from atlas.speech.transcriber import LOCAL_PROVIDER, create_transcriber_chain
from atlas.speech.vosk_engine import SpeechEngineError
from atlas.utils.paths import get_config_path, get_log_dir

logger = get_logger("core")

_VOICE_START_ERRORS = (
    VoiceUnavailableError,
    SpeechEngineError,
    sounddevice.PortAudioError,
    OSError,
    ValueError,
)


class AtlasCore:
    def __init__(
        self,
        app_factory: Callable[[], Application] = Application,
        voice_factory: Callable[..., Voice] = create_voice,
    ) -> None:
        self.events = EventBus()
        self._app_factory = app_factory
        self._voice_factory = voice_factory
        # Guards swapping the app/voice loop (reload, voice toggle, shutdown).
        self._lock = threading.RLock()
        self._app: Application | None = None
        self._voice: Voice | None = None
        self._voice_error = ""
        self._speech_providers: list[str] = []

    @property
    def app(self) -> Application:
        assert self._app is not None, "AtlasCore.start() must be called first"
        return self._app

    def start(self, *, voice: bool = True) -> None:
        with self._lock:
            self._app = self._new_app()
            if voice:
                self.set_voice(True)
        logger.info("ATLAS core started")

    def _new_app(self) -> Application:
        app = self._app_factory()
        app.bootstrap()
        assert app.config is not None
        speech = app.config.speech
        if speech.engine == "vosk":
            chain = create_transcriber_chain(speech)
            self._speech_providers = [t.name for t in chain.transcribers] + [LOCAL_PROVIDER]
        else:
            # OS engine first (it does its own "native" layer), then the remaining layers.
            rest = [p for p in speech.providers if p != "native"]
            chain = create_transcriber_chain(dataclasses.replace(speech, providers=rest))
            self._speech_providers = [speech.engine] + [t.name for t in chain.transcribers]
        return app

    def _on_voice_event(self, kind: str, message: str) -> None:
        if kind == "voice_lost":  # the loop ended itself; nothing left to stop
            # No lock: stop() may hold it while joining this very thread.
            self._voice = None
            self._voice_error = message
            self.events.publish("voice", "unavailable", error=message)
            return
        self.events.publish(kind, message, source="voice")

    # -- commands -----------------------------------------------------------

    def run_command(self, text: str, source: str = "api") -> dict[str, Any]:
        self.events.publish("heard", text, source=source)
        result = self.app.run_text_command(text)
        self.events.publish("result" if result.success else "failed", result.message, source=source)
        return {"success": result.success, "message": result.message}

    # -- voice --------------------------------------------------------------

    def set_voice(self, enabled: bool) -> bool:
        """Returns whether voice is now running; failures land in status()."""
        with self._lock:
            if not enabled:
                if self._voice is not None:
                    self._voice.stop()
                    self._voice = None
                    self.events.publish("voice", "off")
                return False
            if self._voice is not None:
                return True
            try:
                voice = self._voice_factory(self.app, on_event=self._on_voice_event)
                voice.start()
            except _VOICE_START_ERRORS as exc:
                self._voice_error = str(exc)
                logger.warning("Voice unavailable: %s", exc)
                self.events.publish("voice", "unavailable", error=self._voice_error)
                return False
            self._voice = voice
            self._voice_error = ""
            self.events.publish("voice", "on")
            return True

    # -- status / inspection ------------------------------------------------

    def status(self) -> dict[str, Any]:
        config = self.app.config
        assert config is not None
        return {
            "version": __version__,
            "pid": os.getpid(),
            "voice": {"enabled": self._voice is not None, "error": self._voice_error},
            "speech_providers": self._speech_providers,
            "wake_phrase": config.wake.phrase,
        }

    def plugins(self) -> list[dict[str, str]]:
        return [
            {"name": r.name, "status": r.status.name.lower(), "reason": r.reason}
            for r in self.app.plugin_registry.all()
        ]

    def logs(self, lines: int = 200) -> list[str]:
        path = get_log_dir() / "atlas.log"
        if not path.exists():
            return []
        with path.open(encoding="utf-8", errors="replace") as log_file:
            return [line.rstrip("\n") for line in deque(log_file, maxlen=max(1, lines))]

    # -- config -------------------------------------------------------------

    def config(self) -> dict[str, Any]:
        assert self.app.config is not None
        return asdict(self.app.config)

    def update_config(self, raw: dict[str, Any]) -> None:
        """Validates, saves, then reloads. Raises ConfigError on bad input,
        before anything is written."""
        config = config_from_dict(raw)
        save_config(get_config_path(), config)
        self.reload()

    def discover_apps(self) -> dict[str, list[str]]:
        from atlas.platform import get_backend
        from atlas.platform.discovery import merge_discovered_apps

        config = self.app.config
        assert config is not None
        result = merge_discovered_apps(config, get_backend().discover_applications())
        if result.added or result.updated:
            save_config(get_config_path(), config)
            self.reload()
        return {"added": sorted(result.added), "updated": sorted(result.updated)}

    def reload(self) -> None:
        """Re-reads config from disk and rebuilds the Application (and the
        voice loop, if it was on) so every setting takes effect."""
        with self._lock:
            voice_was_on = self._voice is not None
            self.set_voice(False)
            old = self._app
            self._app = self._new_app()
            if old is not None:
                old.shutdown()
            if voice_was_on:
                self.set_voice(True)
        self.events.publish("reloaded", "Configuration reloaded")

    def shutdown(self) -> None:
        with self._lock:
            self.set_voice(False)
            if self._app is not None:
                self._app.shutdown()
        self.events.close()
        logger.info("ATLAS core stopped")
