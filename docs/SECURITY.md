# Security

## Hard rules

- ATLAS never executes raw speech/text as a shell command. The only path
  from text to execution is: `normalize -> parse (registered grammar) ->
  registered Command class -> validate -> dispatch`. See
  `atlas.commands.parser` and `atlas.commands.dispatcher`.
- `atlas.utils.process.launch_executable` never sets `shell=True` and
  requires a path that already exists on disk - it is not a generic
  command runner.
- No telemetry by default. No microphone recording persisted by default.
  See Atlas.md sections 67-69.

## Confirmation gate

`atlas.security.permissions`:

```python
DANGEROUS_COMMAND_NAMES = {
    "shutdown_computer", "restart_computer", "logout",
    "delete_file", "format_drive", "factory_reset", "terminate_process",
}
```

`requires_confirmation(name, confirmations_enabled=...)` returns `True` for
any name in that set unless confirmations are globally disabled in config -
and even then, the command's own registration decides whether to honor
that (nothing currently disables it). `CommandDispatcher.dispatch`
raises `AwaitingConfirmation` rather than executing when this gate applies
and `confirmed=False`.

## Core service API

The background core (`atlas.service`) listens on `127.0.0.1` only, on a
random port. Every request needs `Authorization: Bearer <token>`, where
the token is freshly generated per start and stored with the port in
`<app data>/core.json`, readable only by the user's profile. Browsers
cannot attach that header cross-origin without a CORS preflight, which the
server never answers, so a web page can't drive ATLAS. `PUT /api/config`
type-checks every field and saves nothing if validation fails.
`/api/command` goes through the same parser/registry/confirmation path as
voice; there is no endpoint that runs arbitrary programs.

## Plugin isolation

A plugin runs arbitrary Python at load time. `atlas.plugins.loader` catches
every exception per-plugin and disables just that plugin - this limits
*crash* blast radius, not *trust* - only install plugins you trust the
source of, the same as any Python package.

## Secrets

Never commit secrets. `.env.example` documents the Spotify OAuth variables
a user fills into their own `.env` (git-ignored). `atlas.logging_setup`
redacts common secret-shaped substrings (`password=`, `client_secret=`,
`access_token=`, `refresh_token=`, `api_key=`) from every log line as a
defense-in-depth measure - it is not a substitute for not logging secrets
in the first place.

Spotify's refresh token specifically is stored in **Windows Credential
Manager**, not config or `.env` (`atlas.integrations.spotify.token_store` -> `atlas.platform.win32.credentials`,
using `win32cred` - no extra dependency). Access tokens are never
persisted at all: they're re-derived from the refresh token on demand and
kept only in memory (`SpotifyClient`), since they're short-lived and
cheap to refresh. `atlas spotify-logout` deletes the stored credential.

## Reporting a vulnerability

This is a pre-release local project; open an issue against the repository
describing the problem. Do not include exploit details for destructive
system actions (shutdown/format/etc.) beyond what's needed to reproduce.
