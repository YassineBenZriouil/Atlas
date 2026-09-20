# Troubleshooting

## `atlas --diagnose` reports `[FAIL] Configuration`

Your `%APPDATA%\Atlas\config.toml` is either corrupt or declares a
`config_version` newer than this build supports. Back up and remove the
file to regenerate defaults, or fix the TOML syntax reported in the error.

## `atlas --diagnose` shows a lot of `[WARN] ... Implemented in Phase 2`

Expected in Phase 1. Microphone, speech recognition, wake detection, Win32
window/monitor control, TTS, and Spotify auth are not implemented yet -
see `Atlas.md` section 79 for the Phase 2 implementation order.

## A plugin doesn't load

Run `atlas --list-plugins`. A disabled plugin's reason is printed directly;
it is also in the log file (`%APPDATA%\Atlas\logs\atlas.log`). ATLAS keeps
running regardless - a broken plugin never takes down core functionality.

## Tests fail with a permissions/access error under `%APPDATA%`

`tests/conftest.py` should redirect `%APPDATA%` to a temp directory for
every test. If you see real-profile paths in a failure, check you're
running via `uv run pytest` (so the fixture and package are on the same
interpreter) rather than a stray global `pytest`.

## Where are the logs?

`%APPDATA%\Atlas\logs\atlas.log`, rotated (`logging.max_bytes` /
`logging.backup_count` in config). Logs never contain passwords, tokens, or
API keys - see `atlas.logging_setup.RedactingFilter`.
