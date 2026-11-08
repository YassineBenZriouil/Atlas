# Roadmap: cross-platform, layered speech, background core + full UI

This plan replaces the "Windows-only, Vosk-only, tray-only" shape of
Phases 1-2. It amends Atlas.md section 0 in one place: cloud speech
recognition is now allowed **as an opt-in fallback** (see Phase 1). Every
other principle in section 0 still holds.

| Phase | Goal | Status |
|---|---|---|
| 1 | Speech: Windows (Win+H) engine by default; Vosk + native/cloud chain optional | Done |
| 2 | `atlas-core` background service with a local API | Done |
| 3 | Full desktop window (replaces the tray icon) | Done |
| 4 | Platform layer: Windows today, macOS/Linux backends later | Done |

---

## Speech recognition: the three-layer rule (target design)

Every OS tries the same three layers, in this order. A layer that doesn't
exist on an OS, isn't set up, fails or hears nothing hands over to the next:

| Layer | What | Windows | macOS | Linux |
|---|---|---|---|---|
| 1. OS recognizer | the OS's own voice recognition | Win+H recognizer (`Windows.Media.SpeechRecognition`) | Dictation (`SFSpeechRecognizer`) - planned | none - skipped |
| 2. Remote | cloud API (`ATLAS_STT_API_KEY`) | yes | yes | yes |
| 3. Local model | offline model (Vosk) | yes | yes | yes |

So Linux starts at layer 2, and with no API key it goes straight to the
local model. macOS development hasn't started; when it does, layer 1 is
Dictation, added as a voice engine in its platform backend (see Phase 4).

**Implemented today vs. this target:**

- `engine = "vosk"` follows the rule exactly: layer 1 (`native`, SAPI on
  Windows), layer 2 (`cloud`), layer 3 (Vosk), configured in
  `[speech] providers`. It needs a Vosk model for the wake word.
- `engine = "windows"` (the default): layer 1 is Windows' on-device
  recognizer constrained to ATLAS's command vocabulary; anything it can't
  match (free-text commands) goes to the cloud API if a key is set. Layer 3 (Vosk) isn't wired into this engine
  yet; it would need a Vosk model plus a small transcriber that feeds it
  the recorded command.

## Phase 1 - Speech recognition

**Default on Windows: `[speech] engine = "windows"`**
(`atlas.platform.win32.voice.WindowsVoiceLoop`). No model download, no
account, no API key, and no Windows privacy setting to change.

- Wake word: `Windows.Media.SpeechRecognition` (via the `winrt-*`
  packages) with a one-word list grammar, recognized on-device.
- Command: the same on-device recognizer, constrained to the **command
  vocabulary** (`atlas.speech.vocabulary`, Atlas.md section 9 Mode B):
  every exact phrase plus every template filled with real values - app
  names/aliases, folders, monitor and volume words, keys (~5,900 phrases,
  compiles in ~0.25 s). Rebuilt on every reload, so new apps/aliases are
  recognizable at once. A test checks that every phrase parses.
- While it listens, ATLAS also records the utterance
  (`atlas.audio.utterance`). If the grammar can't match (free-text
  commands like "search the web for ..."), the recording goes to the
  remaining `[speech] providers` (cloud if a key is set). Say "Atlas",
  pause, then the command.
- Free dictation was tried and dropped for commands on 2026-11-08: WinRT
  online dictation returned `Status=Unknown` with no text on every
  utterance, and SAPI offline dictation turned "open brave" into "Open
  daily for". No Windows privacy setting needs to be turned on.
- Config v1 files (which always said `engine = "vosk"`) migrate to
  `"windows"`; set it back to `"vosk"` to use the offline path.

**`engine = "vosk"` (offline / non-Windows):** the layered chain below.

**Order:** OS-native recognizer -> cloud API -> local Vosk. A provider is
skipped when it is unavailable (not on this OS, no API key) and falls
through at runtime when it errors (network down, timeout) or hears
nothing. Configured in `[speech] providers` (see `docs/CONFIGURATION.md`).

How it works:

- The **wake word stays local (Vosk), always.** Nothing streams anywhere
  while ATLAS is waiting to be woken up.
- After the wake word, `VoiceLoop` buffers the utterance's raw PCM while
  Vosk runs live on it. Vosk decides when the utterance has ended (its
  endpoint detection), then the buffered audio goes through the
  `TranscriberChain`. If every provider fails, Vosk's own live result is
  used - so Vosk is always the implicit last provider.
- **Native (Windows):** SAPI's in-process dictation recognizer
  (`atlas.platform.win32.sapi`), fed our in-memory buffer through `pywin32`. No
  new dependency, fully offline, audio never written to disk.
- **Cloud:** any OpenAI-compatible `/v1/audio/transcriptions` endpoint
  (OpenAI, Groq, a self-hosted Whisper server...). API key from `.env`
  (`ATLAS_STT_API_KEY`), never from config, never logged. Only the
  post-wake utterance is sent, never ambient audio.
- **macOS/Linux native:** no backend yet; `"native"` is skipped there.
  macOS will plug in Dictation (`SFSpeechRecognizer`) through its backend's
  `native_transcriber` / `voice_engines`; Linux has no OS recognizer, so it
  always starts at the remote layer.

## Phase 2 - Background core service

Discord-style: closing the window doesn't stop ATLAS.

- `atlas-core`: one background process owning `Application`, `VoiceLoop`,
  plugins and config. Single instance (second launch just opens the UI).
- Local API on `127.0.0.1` only (stdlib HTTP + Server-Sent Events, no new
  dependency): status, event stream (state changes, transcripts, which
  speech provider handled each utterance, results), run text command,
  config read/write, plugin list, logs, voice on/off, quit.
- Every request needs a random token written to the user's app-data
  directory at startup, so web pages and other users can't drive it.
- `atlas start` = start the core if it isn't running, then open the
  window. `atlas console` / `atlas diagnose` keep working as today.

As built (`atlas.service`):

| Piece | Module |
|---|---|
| Core (app + voice + event history, reload, config) | `atlas.service.core.AtlasCore` |
| HTTP API + SSE | `atlas.service.server.CoreServer`, `run_core()` |
| Discovery, client, detached launch | `atlas.service.client` |
| Event fan-out | `atlas.service.events.EventBus` |

Discovery file: `<app data>/core.json` (`port`, `token`, `pid`), written
once the server is listening and removed on clean exit. A stale file is
harmless: clients ping it and start a fresh core if nothing answers.

| Method | Path | Body / result |
|---|---|---|
| GET | `/api/status` | version, pid, voice `{enabled, error}`, speech providers, wake phrase |
| GET | `/api/events` | SSE: `data: {id, time, kind, message, source?, error?}` |
| GET | `/api/history` | last 200 events |
| POST | `/api/command` | `{"text": "..."}` -> `{success, message}` |
| POST | `/api/voice` | `{"enabled": bool}` -> voice status |
| GET/PUT | `/api/config` | whole config as TOML-shaped JSON; PUT validates, saves, reloads |
| POST | `/api/reload` | re-read config, rebuild app (+ voice if it was on) |
| GET | `/api/plugins` | `[{name, status, reason}]` |
| GET | `/api/logs?lines=N` | last N log lines |
| POST | `/api/apps/discover` | `{added, updated}` |
| POST | `/api/quit` | stop the core |

Event kinds: `heard`, `result`, `failed`, `engine` (which speech
provider recognized the utterance), `status` (`sleeping` / `listening` /
`recognizing` / `processing`), `wake`, `timeout`, `voice`
(`on` / `off` / `unavailable`), `reloaded`.

CLI (every command is `atlas <command>`): `atlas start` (start core if
needed + open the window), `atlas core` (run the core in the
foreground), `atlas status`, `atlas stop`, `atlas reload`.

## Phase 3 - Full desktop window

PySide6 Qt Widgets (already a dependency - no Electron, no web runtime).
A separate client of the Phase 2 API; closing it leaves the core running.

- Live state (sleeping / listening / recognizing / working) with a
  pulsing indicator, voice on/off, and a banner explaining why voice is
  unavailable (with a shortcut to Windows' speech settings).
- History: what was heard, which engine recognized it, the result.
- Text command box (same path as `--console`).
- Applications and aliases editor (filter, add, remove, "discover apps").
- Plugins (loaded/disabled + reason), settings (engine, wake word, listen
  time, Vosk-only options, confirmations, log level), logs, "Quit ATLAS".
- The tray icon is removed.

Not done: a live mic-level meter (the Windows engine doesn't expose audio
levels).

As built (`atlas.ui`): `window.MainWindow` (shell, connection handling,
single instance via a `QLocalServer` named `atlas-window` - launching again
focuses the open window), `pages` (one class per page), `bridge.CoreBridge`
(all API calls and the SSE stream on worker threads, results delivered to
the UI thread through Qt signals; reconnects automatically and re-reads
discovery, so a restarted core is picked up), `theme`.

Launch: `atlas start` (from a terminal) or `.venv\Scripts\atlas-gui.exe`
(`[project.gui-scripts]`, no console window - pin it or make a shortcut).
Closing the window only closes the window.

## Phase 4 - Platform layer

Everything above the OS (commands, parser, core, window, plugins) uses
only the interfaces in `atlas.platform`; `atlas.platform.get_backend()`
picks this OS's implementations by `sys.platform`.

| Piece | Where |
|---|---|
| Interfaces: windows, monitors, keyboard (+ key names), mouse, system, applications, secrets | `atlas.platform.*` |
| Shared logic: alias matching, discovered-app merging, key validation | `atlas.platform.applications`, `.discovery`, `.keyboard` |
| `PlatformBackend` (factories, secret store, discovery, OS voice engines, native transcriber, speech readiness), `get_backend()`, `open_path()` | `atlas.platform` |
| Windows backend: Win32 managers, Credential Manager, Start Menu/Store discovery, SAPI, Win+H voice loop | `atlas.platform.win32` |
| Per-OS app-data directory | `atlas.utils.paths` |

On an OS without a backend, ATLAS still runs: config, the core, the
window, typed commands and the Vosk voice engine all work, and every OS
action fails with `PlatformNotSupportedError` ("Window control isn't
supported on linux yet") - a normal failed command, HTTP 501 from the
core API, or a one-line CLI message, never an import crash.

Adding macOS or Linux: write `atlas/platform/<os>/__init__.py` with a
`create_backend()` returning a `PlatformBackend`, implement the
interfaces there (OS recognizers go in `voice_engines`, e.g.
`{"macos": ...}` for `SFSpeechRecognizer`), and add it to
`_BACKEND_MODULES`. Nothing outside that folder changes.
`tests/unit/test_platform.py` keeps Windows-only imports from leaking out
of `atlas.platform.win32`.

Not done (no access to those OSes): the macOS and Linux backends
themselves.
