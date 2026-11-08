# Troubleshooting

## `atlas diagnose` reports `[FAIL] Configuration`

Your `config.toml` (Windows: `%APPDATA%\Atlas`; see
`docs/CONFIGURATION.md` for macOS/Linux) is either corrupt or declares a
`config_version` newer than this build supports. Back up and remove the
file to regenerate defaults, or fix the TOML syntax reported in the error.

## `atlas diagnose` shows `[WARN] Speech engine / model` / `[WARN] Wake detector`

Only shown with `[speech] engine = "vosk"` (the default on Windows is
`"windows"`, which needs no model). No Vosk model was found. Download one into `models/` - see
`models/README.md` - or set `[speech] model_path` in your config to point
at an already-downloaded model elsewhere.

## `atlas diagnose` shows `[WARN] Spotify authentication`

Expected - this diagnostic check isn't wired up yet, even though the Spotify
plugin itself works. Check the plugin's real state with
`atlas list-plugins` (or the window's Plugins page): it loads once
`.env` has the client ID/secret and `atlas spotify-login` has been run.
Spotify is optional and never required for core functionality.

## Voice: the "You said" column shows "(nothing after wake word)"

ATLAS heard "Atlas" but no speech after it. Pause briefly after "Atlas"
(until the dot on the Live page pulses), then speak. If it keeps
happening, check `atlas list-devices` and set `[audio] device` (or the
Microphone field in Settings) to the mic you actually talk into. The log
line `Command recognition: ...` shows what was recorded and what the
recognizer returned.

## Voice is off: Windows blocked the microphone

Allow "Let desktop apps access your microphone" under Settings > Privacy &
security > Microphone, then press "Try again" in the window.

## A plugin doesn't load

Run `atlas list-plugins`. A disabled plugin's reason is printed directly;
it is also in the log file (`logs/atlas.log` in the app-data directory). ATLAS keeps
running regardless - a broken plugin never takes down core functionality.

## Tests fail with a permissions/access error under the app-data directory

`tests/conftest.py` should redirect the app-data directory (`%APPDATA%` /
`$XDG_DATA_HOME`) to a temp directory for every test. If you see real-profile paths in a failure, check you're
running via `uv run pytest` (so the fixture and package are on the same
interpreter) rather than a stray global `pytest`.

## Where are the logs?

`logs/atlas.log` in the app-data directory (Windows:
`%APPDATA%\Atlas\logs\atlas.log`), rotated (`logging.max_bytes` /
`logging.backup_count` in config). Logs never contain passwords, tokens, or
API keys - see `atlas.logging_setup.RedactingFilter`. The window's Logs page
shows the last 500 lines and has an "Open log folder" button.
