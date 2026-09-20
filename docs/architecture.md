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

## Phase 2 implementation status

Every Windows-layer interface now has a concrete, Win32-backed
implementation, all verified against real windows/monitors/audio on a
real machine (not just mocked):

- `Win32WindowManager` / `Win32MonitorManager` / `Win32ApplicationManager`
  (`atlas.windows`) - real window enumeration, focus (via
  `AttachThreadInput`, working around Windows' foreground-lock
  restriction), move/resize/minimize/maximize/close, monitor enumeration,
  and application discovery (PATH, the registry's "App Paths" key,
  configured executable paths).
- `Win32KeyboardController` / `Win32MouseController` - real `keybd_event`/
  `mouse_event` input.
- `Win32SystemController` - real volume via `pycaw`, lock/sleep via
  `ctypes`, shutdown/restart via a fixed `shutdown.exe` command line
  (never voice-input-derived), screenshots via Qt's `QScreen.grabWindow`.
- `SoundDeviceMicrophone` / `SoundDeviceAudioStream` (`atlas.audio`) -
  real device enumeration and PCM capture via `sounddevice`.
- `VoskSpeechEngine` / `VoskWakeDetector` (`atlas.speech`, `atlas.wake`) -
  real offline recognition against a downloaded Vosk model; the wake
  detector uses a grammar constrained to just the wake phrase.
- `atlas.application.voice_loop.VoiceLoop` - the piece that actually
  drives the pipeline continuously: microphone -> wake detector -> speech
  engine -> `Application.run_text_command`, on a background thread.

Still not implemented: the Spotify/browser-extension-free web search is
done, but the Spotify plugin itself, and the macro engine (Atlas.md
sections 27, 46), are future work.

## Command grammar

`atlas.commands.parser.CommandParser` now has three layers, tried in
order:

1. Exact phrases (`Grammar` / `add_grammar`) - the Phase 1 developer
   commands.
2. Templated patterns (`PatternGrammar` / `add_pattern`) - e.g.
   `"open {application}"`, `"resize {application} to {width} by
   {height}"`. Entities are extracted as raw strings; alias/path
   resolution happens in the command's `execute()`, not at parse time, so
   an unresolvable name is a normal execution failure
   ("'photoshop' was not found"), not a parser guess.
3. Custom matchers (`add_custom_matcher`) - currently just the one
   multi-turn clarification flow the spec names explicitly (sections
   28-29): a bare `"move brave"` with no monitor/direction returns a
   `NeedsClarification("Which monitor?")` instead of guessing, and
   `Application` remembers it as `_pending_clarification` until the next
   utterance resolves or abandons it. The same mechanism
   (`_pending_confirmation`) gates dangerous commands behind an explicit
   "confirm".

## Testability without disrupting the desktop

Real Win32 calls that are read-only (monitor/window enumeration,
locating an app by path) run in the normal `pytest` suite. Anything that
pops a visible window, changes system volume, or drives real audio
hardware is either:

- exercised against fakes (`tests/fixtures/fakes.py` implements every
  Windows-layer ABC in memory) for command-level and `Application`-level
  logic, including the confirmation/clarification flows - a test can
  prove "shutdown never runs without confirm" without ever touching
  `Win32SystemController`, or
- gated behind `ATLAS_TEST_DESKTOP=1` (`tests/integration/test_desktop_live.py`)
  for the handful of tests that genuinely need to open/move a real window
  or touch real volume, or
- driven with **real** speech recognition against **locally synthesized**
  audio: the TTS engine speaks a phrase to a WAV file, which is fed
  through the real `VoskWakeDetector`/`VoskSpeechEngine`/`VoiceLoop` -
  proving actual recognition works without a human speaker or any
  network access (`tests/integration/test_speech_recognition.py`,
  `test_voice_loop.py`; both skip cleanly if no model is downloaded).

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
