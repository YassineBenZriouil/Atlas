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
