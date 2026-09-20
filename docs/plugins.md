# Plugin Development

## Interface

```python
from atlas.plugins.base import AtlasPlugin, PluginContext
from atlas.commands.registry import CommandRegistry

class MyPlugin(AtlasPlugin):
    name = "my_plugin"

    def initialize(self, context: PluginContext) -> None:
        ...

    def register_commands(self, registry: CommandRegistry) -> None:
        registry.register(MyCommand)

    def shutdown(self) -> None:
        ...

PLUGIN_CLASS = MyPlugin
```

## Where to put it

- `plugins/my_plugin/__init__.py`, or
- `plugins/my_plugin.py`

Either way, the module must expose `PLUGIN_CLASS` at module scope.

## Discovery and isolation

`atlas.plugins.loader.PluginLoader.discover_and_load` scans a directory,
and for each candidate:

1. imports the module,
2. validates `PLUGIN_CLASS` is an `AtlasPlugin` subclass with a non-empty `name`,
3. instantiates it, calls `initialize()`, then `register_commands()`,
4. records it as loaded in `PluginRegistry`.

**Any exception at any step disables that one plugin** - it is logged with
a reason and recorded in `PluginRegistry` as `DISABLED`; every other
plugin, and ATLAS itself, keeps running (Atlas.md section 44). See
`tests/fixtures/plugins/` for a minimal working plugin and a deliberately
broken one, and `tests/integration/test_plugin_loader.py` for the isolation
test.

## First-party integrations

`src/atlas/integrations/{spotify,browser,filesystem}` are first-party
plugins shipped with ATLAS itself. Browser and filesystem are wired
directly into `Application.bootstrap()` (they're core-ish per Atlas.md's
own command categories, sections 21/23/26). Spotify is different: it's
genuinely optional and load-bearing on external state (a Spotify account,
OAuth), so it goes through the *real* isolation path -
`PluginLoader.load_plugin_class(SpotifyPlugin)` - the same
initialize/register_commands/mark_loaded-or-disabled sequence a
third-party plugin in `plugins/` gets, just skipping the filesystem
import step since it's already part of the installed package.

## Spotify plugin (a worked example of "optional")

Setup (see `docs/configuration.md` and `.env.example`):

1. Register an app at https://developer.spotify.com to get a client
   ID/secret.
2. Copy `.env.example` to `.env`, fill in
   `ATLAS_SPOTIFY_CLIENT_ID`/`ATLAS_SPOTIFY_CLIENT_SECRET`.
3. Run `atlas --spotify-login` once - it opens a browser for Spotify's own
   sign-in/consent screen, catches the redirect on a local
   `http://127.0.0.1:8888/callback` server, and stores only the resulting
   **refresh token** in Windows Credential Manager
   (`atlas.integrations.spotify.token_store`) - never in config, never in
   logs.
4. `atlas --spotify-logout` forgets it again.

`SpotifyPlugin.initialize()` checks for both the env vars and a stored
refresh token; missing either raises, which `PluginLoader` turns into a
clean `DISABLED` record with the reason ("...see .env.example" or "...run
`atlas --spotify-login`") rather than blocking ATLAS startup - the same
mechanism `tests/integration/test_spotify_plugin.py` exercises for real,
with no Spotify account needed to prove it works.

Runtime API calls (`atlas.integrations.spotify.client.SpotifyClient`) go
only to Spotify's official Web API over HTTPS - no scraping, no audio
download, no bypassing Spotify's own auth (Atlas.md section 27).
