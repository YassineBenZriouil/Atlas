# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ATLAS: a local, deterministic, voice-controlled desktop assistant (Windows 10/11 is the only full
platform backend so far; Python 3.12+, `uv`).
`Atlas.md` is the full spec and is treated as the **engineering contract** — read its section 0
before making design decisions, and `docs/ROADMAP.md` for the current 4-phase plan (cross-platform,
layered speech, background core + full window) which amends it. Non-negotiables: no LLM / generative AI,
no cloud speech recognition except the opt-in post-wake fallback, no mandatory paid service, no telemetry, no unnecessary dependencies, deterministic
command interpretation, never silently execute destructive operations, all local features must work
offline. Current phase and command list: `README.md` and `docs/COMMANDS.md`.

## Commands

```powershell
uv sync                              # install runtime + dev deps into .venv
uv run pytest                        # full suite (desktop-live tests skipped by default)
uv run pytest tests/unit/test_parser.py::test_name -v   # single test
uv run pytest -k parser -v
uv run ruff check .
uv run ruff format .
uv run mypy src

# Every CLI command is a subcommand: `atlas <command>` (list: `atlas`; table: COMMANDS in __main__.py)
uv run atlas start                   # run ATLAS: open the window; starts the background core (detached) if needed
uv run atlas core                    # run the core in the foreground (what the detached process runs)
uv run atlas status | stop | reload
uv run atlas console                 # type commands as text; best way to exercise the pipeline without a mic
uv run atlas diagnose                # check what's working
uv run atlas discover-apps           # scan Start Menu + Store apps into config
start.cmd                            # uv sync + `atlas diagnose` + `atlas start`
```

Test gating:
- `tests/integration/test_desktop_live.py` (opens/moves real windows, changes volume) only runs with
  `$env:ATLAS_TEST_DESKTOP = "1"`.
- Speech/wake tests (`test_speech_recognition.py`, `test_voice_loop.py`) skip unless a Vosk model is
  under `models/` (see `models/README.md`). They synthesize their own audio via local TTS.
- `tests/conftest.py` redirects the app-data dir to `tmp_path` and swaps the OS secret store for an
  in-memory one in every test, so tests never touch real config or stored credentials.

## Architecture

One rule: `INPUT -> INTERPRETATION -> COMMAND -> VALIDATION -> EXECUTION`, each a separate module.

```
Microphone -> AudioStream -> WakeDetector -> SpeechEngine -> RecognitionResult
  -> normalize() -> CommandParser -> Command -> CommandDispatcher
  -> atlas.platform managers / plugins -> CommandResult -> feedback (TTS)
```

- `atlas.application.voice_loop.VoiceLoop` drives mic -> wake -> speech -> `Application.run_text_command`
  on a background thread. `--console` feeds text straight into `run_text_command`.
- `Application.bootstrap()` (`atlas.application.app`) wires everything: registers builtin commands/grammars,
  browser and filesystem integrations directly, and Spotify through `PluginLoader.load_plugin_class`
  (the real isolation path, so a missing token/env var disables it instead of breaking startup).
- `atlas.application.state.StateMachine`: `SLEEPING -> WAKE_DETECTED -> LISTENING -> RECOGNIZING -> PARSING
  -> VALIDATING -> EXECUTING -> FEEDBACK -> SLEEPING`; any state can fail to `ERROR -> RECOVERY -> SLEEPING`.

**Speech target design (user's rule):** every OS tries 3 layers in order: 1. the OS's own recognizer
(Windows: on-device recognizer constrained to the command vocabulary; macOS: Dictation, not built yet;
Linux: none, so skipped), 2. remote/cloud
API, 3. local model (Vosk). Keep new speech work consistent with this; see `docs/ROADMAP.md`.
Gap today: the `windows` engine runs layers 1-2 but not layer 3 (Vosk).

**Speech:** `[speech] engine` picks the voice loop via `voice_loop.create_voice`. `"windows"` (default
on Windows) = `atlas.platform.win32.voice.WindowsVoiceLoop`: WinRT on-device wake grammar, then a WinRT
list grammar of the whole command vocabulary (`atlas.speech.vocabulary`, built from the parser + config;
`test_every_vocabulary_phrase_parses` keeps them in sync). The utterance is recorded in parallel
(`atlas.audio.utterance`) and only goes to the remaining providers (cloud) when the grammar can't match.
Do NOT use free dictation for commands: WinRT online dictation returned Status=Unknown on every
utterance here, and SAPI dictation heard "open brave" as "Open daily for".
`"vosk"`: wake word is local Vosk. After wake, `VoiceLoop` buffers the utterance PCM while Vosk
endpoints it live, then `atlas.speech.transcriber.TranscriberChain` tries `[speech] providers` in order
(`native` = the backend's native transcriber, SAPI on Windows, `cloud` = OpenAI-compatible API keyed by `ATLAS_STT_API_KEY`); errors/empty
results fall through, and Vosk's live text is the implicit last fallback.

**Core service** (`atlas.service`): `AtlasCore` owns the `Application`, the `VoiceLoop` and an
`EventBus`; `CoreServer` exposes it over stdlib HTTP + SSE on 127.0.0.1 with a per-start bearer token
from `<app data>/core.json`; `atlas.service.client` finds/starts/talks to it. Reload = build a fresh
`Application` (config changes never mutate a live one). API reference: `docs/ROADMAP.md` Phase 2.
`Application.run_text_command` holds a lock because voice and API threads both call it.

**Window** (`atlas.ui`): PySide6 client of the core API only - never imports `Application`. All API
calls go through `bridge.CoreBridge` (worker threads -> Qt signals); never call the client from the UI
thread. Tests run it offscreen against a fake client (`tests/unit/test_window.py`).

**Platform layer** (`atlas.platform`): interfaces + shared logic (alias matching, discovery merge, key
names). `get_backend()` returns this OS's `PlatformBackend` (manager factories, `SecretStore`, app
discovery, OS voice engines, native transcriber). `atlas.platform.win32` is the only full backend;
other OSes get a fallback whose actions raise `PlatformNotSupportedError`. New OS = new
`atlas/platform/<os>/` + an entry in `_BACKEND_MODULES` (see `docs/ROADMAP.md` Phase 4).

**Parser** (`atlas.commands.parser.CommandParser`) tries three layers in order:
1. exact phrases (`Grammar` / `add_grammar`),
2. templated patterns (`PatternGrammar` / `add_pattern`, e.g. `"open {application}"`) — entities are
   extracted as raw strings; alias/path resolution happens in the command's `execute()`, so an
   unknown name is a normal execution failure, not a parser guess,
3. custom matchers (`add_custom_matcher`) — e.g. `"move brave"` returns `NeedsClarification("Which monitor?")`.

Multi-turn state lives on `Application`: `_pending_clarification` (resolved/abandoned by the next utterance)
and `_pending_confirmation` (dangerous commands like shutdown/restart require an explicit "confirm";
see `atlas.security.permissions`).

**Adding a command:** implement `atlas.commands.command.Command` (`validate`, `execute`, `describe`),
register it in the registry, add a grammar/pattern, add a parser unit test, and a permissions test if dangerous.

## Rules that span the codebase

- Nothing outside `atlas.platform.win32` imports Windows-only modules (`win32*`, `pythoncom`, `pycaw`,
  `winreg`, `winrt`) or `atlas.platform.win32` — `tests/unit/test_platform.py` enforces it. Commands use
  the `atlas.platform` interfaces. `tests/fixtures/fakes.py` implements every interface in memory; use it for command- and
  `Application`-level tests instead of touching the desktop.
- Only two places may catch broad `Exception`: `CommandDispatcher.dispatch` and
  `Application.run_text_command`. Both log and return `CommandResult.fail(...)`. No bare/swallowed excepts elsewhere.
- Shutdown/restart use a fixed `shutdown.exe` command line — never build process args from voice input.
- Plugins: `src/atlas/plugins/` is the interface + loader; `src/atlas/integrations/` holds first-party
  plugins (core never imports them directly except via bootstrap wiring); top-level `plugins/` is for
  user plugins exposing `PLUGIN_CLASS`. Any exception in a plugin disables only that plugin. See `docs/PLUGINS.md`.
- Spotify secrets: client ID/secret from `.env` (`.env.example`); refresh token only in the backend's
  `SecretStore` (Windows Credential Manager) — never in config or logs (`RedactingFilter` in `atlas.logging_setup`).
- Commit style: `feat: ...`, `fix: ...`, `test: ...`, `docs: ...`.
