# Troubleshooting

## `atlas --diagnose` reports `[FAIL] Configuration`

Your `%APPDATA%\Atlas\config.toml` is either corrupt or declares a
`config_version` newer than this build supports. Back up and remove the
file to regenerate defaults, or fix the TOML syntax reported in the error.

## `atlas --diagnose` shows `[WARN] Speech engine / model` / `[WARN] Wake detector`

No Vosk model was found. Download one into `models/` - see
`models/README.md` - or set `[speech] model_path` in your config to point
at an already-downloaded model elsewhere.

## `atlas --diagnose` shows `[WARN] Spotify authentication`

Expected - the Spotify plugin isn't implemented yet (it's optional per
Atlas.md sections 27/59 and never required for core functionality).

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
