# Development

## Setup

```powershell
uv sync
```

This creates `.venv/` and installs both runtime and dev dependency groups
(`pytest`, `ruff`, `mypy`).

## Project layout

```
src/atlas/          # the package
tests/unit/         # fast, no I/O beyond tmp_path
tests/integration/  # multi-module (plugin loader, full pipeline)
tests/fixtures/     # sample plugins etc. used by integration tests
```

`tests/conftest.py` redirects `%APPDATA%` to a pytest `tmp_path` for every
test automatically - tests never touch your real ATLAS configuration.

Tests that would open/move a real window or touch system volume are
skipped by default and gated behind an env var:

```powershell
uv run pytest                              # skips tests/integration/test_desktop_live.py
$env:ATLAS_TEST_DESKTOP = "1"; uv run pytest tests/integration/test_desktop_live.py
```

Speech/wake tests (`test_speech_recognition.py`, `test_voice_loop.py`)
skip cleanly if no Vosk model is present under `models/` - download one
per `models/README.md` to run them; they synthesize their own test audio
via the local TTS engine, so no human speaker or network access is needed
once the model is downloaded.

## Running things

```powershell
uv run atlas --diagnose
uv run atlas --tray
uv run pytest
uv run pytest -k parser -v
uv run ruff check .
uv run ruff format .
uv run mypy src
```

## Adding a command

1. Implement `atlas.commands.command.Command` in the relevant module.
2. Register it: `registry.register(MyCommand)`.
3. Add a grammar: `parser.add_grammar(Grammar("my_command", ("phrase one", "phrase two")))`.
4. Add a unit test exercising `parser.parse(...)` and, if it's dangerous,
   a test against `atlas.security.permissions`.

## Adding a plugin

See `docs/plugins.md`.

## Code style

- `ruff` for linting/formatting, `mypy` for types (see `pyproject.toml` for
  configured rules).
- No bare `except:` / no swallowed exceptions. The dispatcher and
  `Application.run_text_command` are the only two places that catch broad
  `Exception`, and they always log and return a structured failure.
- No command implementation reaches into Win32 directly - go through
  `atlas.windows`.
- Small, focused modules. See Atlas.md section 80 for the full DO/DON'T list.

## Commit style

```
feat: add command registry
fix: recover from microphone disconnect
test: add parser fixtures
docs: document plugin architecture
```
