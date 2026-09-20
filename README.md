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
and a real settings UI - see `docs/commands.md` for the exact command
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

```powershell
uv run atlas --diagnose      # check what's working
uv run atlas --console       # type commands as text (no mic/wake word needed - good for testing)
uv run atlas --tray          # start the tray application (voice via "Enable voice")
uv run atlas --spotify-login # optional: connect a Spotify account (see docs/plugins.md)
uv run atlas --help          # see all developer flags
```

## Testing

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

## Documentation

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/commands.md`](docs/commands.md)
- [`docs/plugins.md`](docs/plugins.md)
- [`docs/configuration.md`](docs/configuration.md)
- [`docs/development.md`](docs/development.md)
- [`docs/troubleshooting.md`](docs/troubleshooting.md)
- [`docs/security.md`](docs/security.md)

## License

Not yet finalized - see [`LICENSE`](LICENSE). Do not distribute publicly
until this is resolved.
