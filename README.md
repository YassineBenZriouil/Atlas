# ATLAS

Local, deterministic, free voice-controlled Windows assistant.

ATLAS converts speech to text, matches the text against deterministic
grammars, builds a structured command, validates it, and executes a
registered action. **No LLM. No cloud AI. No generative model of any kind.**
See [`Atlas.md`](Atlas.md) for the full specification and engineering
contract this project is built against.

## Status

**Phase 2 - Functional Implementation.** ATLAS actually does things now:
real microphone capture, real offline speech recognition and wake-word
detection (Vosk), real Win32 window/monitor/keyboard/mouse/volume control,
and a real command set (open/close/focus/switch/minimize/maximize/restore
an application, move/resize windows across monitors, volume/mute/lock/
screenshot, keyboard shortcuts, browser tab control, folder opening,
optional Spotify playback). Multi-turn clarification ("Move Brave." ->
"Which monitor?") and the confirmation gate for dangerous commands
(shutdown/restart) both work end-to-end. Not yet done: the macro engine
and a real settings UI - see `docs/COMMANDS.md` for the exact command
list.

## Requirements

- Windows 10/11 x64
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A downloaded [Vosk model](https://alphacephei.com/vosk/models) under
  `models/` (see `models/README.md`) for speech/wake features - everything
  else works without one.

## Setup

```powershell
uv sync
```

## Running

Every command is `atlas <command>`. Inside the repo you can prefix them
with `uv run` (`uv run atlas start`); to type plain `atlas` from any
terminal, install it once as a uv tool (editable, so code changes apply
immediately):

```powershell
uv tool install --editable .
uv tool update-shell   # once, if uv says its tool folder isn't on PATH
```

```powershell
atlas start           # run ATLAS: opens the window (starts the background core if needed)
atlas stop            # stop the background core
atlas status          # is it running, is voice on, which speech engine
atlas reload          # re-read config.toml
atlas diagnose        # check what's working
atlas discover-apps   # scan installed apps (Start Menu + Store) and add them to config
atlas console         # type commands as text (no mic/wake word needed - good for testing)
atlas spotify-login   # optional: connect a Spotify account (see docs/PLUGINS.md)
atlas                 # list every command
```

Voice uses Windows' own built-in speech recognition, offline - no model
download, no account, nothing to turn on. Say "Atlas", pause a moment,
then your command. Closing the window keeps ATLAS listening; use
"Quit ATLAS" in the window (or `atlas stop`) to stop it.
`.venv\Scripts\atlas-gui.exe` opens the window without a console.

## Testing

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

## Documentation

- [`docs/ROADMAP.md`](docs/ROADMAP.md) - current 4-phase plan
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/COMMANDS.md`](docs/COMMANDS.md)
- [`docs/PLUGINS.md`](docs/PLUGINS.md)
- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)
- [`docs/SECURITY.md`](docs/SECURITY.md)

## License

Not yet finalized - see [`LICENSE`](LICENSE). Do not distribute publicly
until this is resolved.
