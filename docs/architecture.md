# Architecture

## The one rule

```
INPUT -> INTERPRETATION -> COMMAND -> VALIDATION -> EXECUTION
```

Never microphone -> giant Python file -> actions. Every stage is a separate,
independently testable module, and no command implementation ever touches
a Win32 API directly.

## Pipeline

```
Microphone -> AudioStream -> WakeDetector -> SpeechEngine -> RecognitionResult
    -> normalize() -> CommandParser -> Command -> CommandDispatcher
    -> WindowManager / ApplicationManager / plugins -> CommandResult -> Feedback
```

Every arrow is a real module boundary in `src/atlas/`:

| Stage | Module |
|---|---|
| Audio capture | `atlas.audio` |
| Wake detection | `atlas.wake` |
| Speech recognition | `atlas.speech` |
| Normalization | `atlas.utils.strings` |
| Parsing | `atlas.commands.parser`, `atlas.commands.matcher`, `atlas.commands.entities` |
| Command model | `atlas.commands.command` |
| Registry | `atlas.commands.registry` |
| Dispatch | `atlas.commands.dispatcher` |
| Windows integration | `atlas.windows` |
| Plugins | `atlas.plugins`, `atlas.integrations.*`, top-level `plugins/` |
| State machine | `atlas.application.state` |
| Orchestration | `atlas.application.app`, `atlas.application.lifecycle` |
| Config | `atlas.config` |
| Logging | `atlas.logging_setup` |
| Security | `atlas.security.permissions` |
| Tray UI | `atlas.ui` |

## State machine

```
SLEEPING -> WAKE_DETECTED -> LISTENING -> RECOGNIZING -> PARSING
    -> VALIDATING -> EXECUTING -> FEEDBACK -> SLEEPING
```

Any state can fail into `ERROR`, which always recovers back to `SLEEPING`
through `RECOVERY`. See `atlas.application.state.StateMachine`. No
uncaught exception is allowed to escape `Application.run_text_command` -
it is the outer safety boundary (Atlas.md section 33).

## Phase 1 vs. Phase 2 boundary

Interfaces that exist as abstract classes today (`WindowManager`,
`ApplicationManager`, `MonitorManager`, `KeyboardController`,
`MouseController`, `SystemController`, `Microphone`, `AudioStream`,
`WakeDetector`) have no concrete Win32/audio-backed implementation yet.
That is intentional - Phase 1's job is the skeleton, not the plumbing
(Atlas.md section 79). What *is* fully implemented and tested in Phase 1:
config, logging, the command pipeline for parameter-less commands, the
plugin loader with isolation, the state machine, and the wake controller's
state-transition logic (independent of real audio).

## Plugins vs. integrations

- `src/atlas/plugins/` - the plugin *interface and loader*, used by everyone.
- `src/atlas/integrations/` - first-party optional plugins shipped with
  ATLAS (Spotify, browser, filesystem). Core never imports these directly.
- top-level `plugins/` - where a user or third party drops their own
  plugin at runtime; discovered the same way as integrations.

## Safety boundary

`CommandDispatcher.dispatch` and `Application.run_text_command` both catch
broad exceptions deliberately - they are the two places in the codebase
allowed to do so, because they convert any command/plugin failure into a
logged, structured `CommandResult.fail(...)` instead of crashing the
process (Atlas.md sections 33, 56).
