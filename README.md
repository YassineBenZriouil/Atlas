# ATLAS

Local, deterministic, free voice-controlled Windows assistant.

ATLAS converts speech to text, matches the text against deterministic
grammars, builds a structured command, validates it, and executes a
registered action. **No LLM. No cloud AI. No generative model of any kind.**
See [`Atlas.md`](Atlas.md) for the full specification and engineering
contract this project is built against.

## Status

**Phase 1 - Foundation & Architecture.** The skeleton exists and runs:
configuration, logging, the command pipeline (parser/registry/dispatcher),
the state machine, the plugin system, and interfaces for speech/audio/
Windows integration. Real Vosk recognition, Win32 window/monitor control,
and the Spotify/browser/filesystem plugins are Phase 2 work.

## Requirements

- Windows 10/11 x64
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup

```powershell
uv sync
```

## Running

```powershell
uv run atlas --diagnose      # check what's working
uv run atlas --tray          # start the tray application
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
