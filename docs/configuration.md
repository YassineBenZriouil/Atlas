# Configuration

## Location

```
%APPDATA%\Atlas\config.toml
```

Created with defaults on first run (`atlas.config.loader.load_config`).
Never hard-code a user-specific path - always go through
`atlas.utils.paths`.

## Schema

Defined as typed dataclasses in `atlas.config.schema`:

```toml
config_version = 1

[audio]
device = "default"
sample_rate = 16000
channels = 1

[speech]
engine = "vosk"
model_path = ""
language = "en-us"

[wake]
phrase = "atlas"
timeout_seconds = 8.0

[tts]
enabled = false
voice = "default"
volume = 1.0

[applications.brave]
executable = ""
aliases = ["brave", "brave browser"]

[commands]
require_confirmation = true
disabled = []

[plugins]
enabled = []
disabled = []

[logging]
level = "INFO"
max_bytes = 5000000
backup_count = 5
```

## Application discovery

```powershell
uv run atlas --discover-apps
```

Scans Start Menu shortcuts (resolved to their real target `.exe` via the
shell) and Store/UWP apps (via `Get-StartApps`, launched through
`shell:AppsFolder\<AppID>` since they have no file path) and merges the
result into config (`atlas.windows.discovery`). Safe to re-run any time
you install something new:

- If a discovered app's name matches an existing key or **alias**, it
  fills in that entry's `executable` only if it's currently empty - it
  never overwrites a path you (or an earlier run) already set.
- Otherwise it adds a new entry, keyed by a slugified version of the
  app's name, with the app's own display name as its only alias.

A Store app's `executable` looks like
`uwp:Microsoft.WindowsNotepad_8wekyb3d8bbwe!App` instead of a file path -
`Win32ApplicationManager` recognizes the `uwp:` prefix and launches it via
Explorer's `shell:AppsFolder` instead of `subprocess`.

## Alias matching for misheard/abbreviated speech

`Win32ApplicationManager.resolve_alias` tries, in order:

1. Exact match against a configured key or alias.
2. Ratio-based fuzzy matching (`difflib`, cutoff 0.75) - catches typos and
   ASR slips like "vs cold" for "vs code", but only against aliases of at
   least 5 characters, since ratio comparisons on short strings are
   unreliable (a couple of shared letters between two 3-character strings
   already looks like a strong match).
3. Prefix matching - catches short, deliberate abbreviations ("disc" for
   "discord", "spot" for "spotify", "set" for "settings") that ratio
   matching is too conservative for. Requires at least 3 characters on
   both sides, and refuses (returns no match) if the abbreviation is a
   prefix of more than one configured alias - Atlas.md section 28 (never
   guess) applies here just as much as anywhere else.

None of this touches command *verbs* - "close"/"open"/etc. are matched by
exact grammar before an application name is ever extracted, so a short
alias can never be confused with a command word.

## Migration

`config_version` is checked on every load. A version newer than the running
ATLAS refuses to load (`ConfigError`) rather than silently corrupting data.
Migrating an older version forward happens in
`atlas.config.loader._migrate` - add a step there when the schema changes;
never delete a user's configuration file to "fix" a mismatch.

## Editing programmatically

```python
from atlas.config.loader import load_config, save_config
from atlas.utils.paths import get_config_path

config = load_config(get_config_path())
config.wake.phrase = "computer"
save_config(get_config_path(), config)
```
