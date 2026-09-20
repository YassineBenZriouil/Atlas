# ATLAS

## Local, Deterministic, Free Voice-Controlled Windows Assistant

**Project codename:** ATLAS
**Target platform:** Windows 10/11 x64
**Primary language:** Python 3.12+
**License:** To be decided before public distribution
**Architecture:** Local-first, deterministic, plugin-based
**AI policy:** NO GENERATIVE AI / NO LLM / NO CLOUD AI
**Cost target:** $0 for core functionality
**Primary developer:** Yassine Ben Zriouil

---

# 0. CLAUDE CODE DIRECTIVE

You are Claude Code working as the principal software architect and implementation engineer for **ATLAS**.

ATLAS is a Windows desktop voice-control assistant.

Your responsibility is to take this specification from an empty repository to a production-ready application.

Do not treat this document as a suggestion.

Treat it as the engineering contract.

You are allowed to make implementation decisions where this specification leaves room for them, but you MUST preserve the following principles:

1. No generative AI.
2. No LLM.
3. No cloud-based speech recognition.
4. No mandatory paid service.
5. No telemetry by default.
6. No unnecessary dependencies.
7. No massive framework for functionality that Windows/Python can provide directly.
8. Deterministic command interpretation.
9. Plugin-based architecture.
10. Testable components.
11. Production-quality error handling.
12. Clear separation between speech recognition, parsing, command execution, UI, and plugins.
13. Never silently execute destructive operations.
14. The application must be usable without an internet connection for all local functionality.
15. Internet-dependent integrations must degrade gracefully.

Do not prematurely implement every feature.

Build according to the three phases defined below.

---

# 1. PRODUCT VISION

ATLAS is a voice-controlled Windows assistant that allows the user to control their computer naturally without requiring an LLM.

The user should eventually be able to say things such as:

> "Atlas"

> "Open Brave"

> "Open VS Code"

> "Close Discord"

> "Move Brave to monitor two"

> "Put VS Code on the main monitor"

> "Maximize Brave"

> "Minimize Spotify"

> "Mute"

> "Set volume to 40"

> "Play"

> "Pause"

> "Next song"

> "Open my work playlist"

> "Search Spotify for Jay-Z"

> "Play Jay-Z"

> "Open Downloads"

> "Open my projects folder"

> "Lock the computer"

> "Take a screenshot"

> "Switch to Brave"

> "Switch to VS Code"

The critical distinction is:

ATLAS does NOT "understand" these requests using an LLM.

Instead, ATLAS converts speech into text, parses the text against deterministic grammars/patterns, creates a structured command, validates it, and executes a registered action.

Example:

```text
USER SPEECH
    ↓
"move brave to monitor two"
    ↓
SPEECH-TO-TEXT
    ↓
"move brave to monitor two"
    ↓
COMMAND PARSER
    ↓
MoveWindowCommand(
    application="brave",
    monitor=2
)
    ↓
VALIDATION
    ↓
WINDOW MANAGER
    ↓
Windows API
```

---

# 2. CORE DESIGN PHILOSOPHY

ATLAS should feel intelligent without actually being AI-driven.

It achieves this through:

* aliases
* grammar rules
* entities
* command composition
* application plugins
* context
* state
* fuzzy matching
* deterministic normalization
* configurable vocabulary

Example:

All of these can map to the same command:

```text
open brave
launch brave
start brave
run brave
fire up brave
```

They become:

```python
OpenApplicationCommand(
    application="brave"
)
```

This is NOT semantic AI.

It is deterministic command matching.

---

# 3. HARD REQUIREMENTS

## 3.1 No AI

ATLAS MUST NOT contain:

* OpenAI API
* Claude API
* Gemini API
* local LLM
* Ollama
* LM Studio
* agent frameworks
* autonomous AI agents
* cloud AI
* AI-based command planning

Do not add an LLM "just to make parsing easier."

The parser must remain deterministic.

---

# 3.2 Free

Core ATLAS functionality must cost nothing.

The following must remain free:

* voice recognition
* wake detection
* command parsing
* Windows control
* application launching
* window management
* keyboard/mouse automation
* system controls
* local configuration
* logging
* plugin system

Optional third-party integrations may require their own accounts or service limitations.

---

# 3.3 Local-first

ATLAS should operate without an internet connection.

Offline functionality includes:

* wake detection
* speech recognition
* command parsing
* application launching
* window management
* keyboard automation
* mouse automation
* system volume
* monitor management where supported
* file/folder opening
* screenshots
* system actions
* plugin loading
* configuration

Internet access is allowed ONLY for features that inherently require it.

Examples:

* Spotify API
* web searches
* online information
* update checking

---

# 4. THREE-PHASE DEVELOPMENT PLAN

The project MUST be developed in exactly three major phases.

---

# PHASE 1 — FOUNDATION & ARCHITECTURE

## Objective

Create the complete project foundation and architecture.

At the end of Phase 1:

* repository exists
* project builds/runs
* dependencies are defined
* architecture exists
* core interfaces exist
* configuration system exists
* logging exists
* plugin architecture exists
* command architecture exists
* speech architecture exists
* Windows integration architecture exists
* test infrastructure exists
* development documentation exists

The assistant does NOT need to be feature-complete yet.

Phase 1 is about creating the skeleton correctly.

---

## 4.1 Repository structure

Target architecture:

```text
atlas/
│
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env.example
│
├── docs/
│   ├── architecture.md
│   ├── commands.md
│   ├── plugins.md
│   ├── configuration.md
│   ├── development.md
│   ├── troubleshooting.md
│   └── security.md
│
├── src/
│   └── atlas/
│       │
│       ├── __init__.py
│       ├── __main__.py
│       │
│       ├── application/
│       │   ├── app.py
│       │   ├── lifecycle.py
│       │   └── state.py
│       │
│       ├── audio/
│       │   ├── microphone.py
│       │   ├── audio_stream.py
│       │   └── devices.py
│       │
│       ├── speech/
│       │   ├── engine.py
│       │   ├── vosk_engine.py
│       │   ├── recognizer.py
│       │   └── result.py
│       │
│       ├── wake/
│       │   ├── detector.py
│       │   └── wake_controller.py
│       │
│       ├── commands/
│       │   ├── command.py
│       │   ├── registry.py
│       │   ├── parser.py
│       │   ├── matcher.py
│       │   ├── entities.py
│       │   └── dispatcher.py
│       │
│       ├── windows/
│       │   ├── applications.py
│       │   ├── windows.py
│       │   ├── monitors.py
│       │   ├── keyboard.py
│       │   ├── mouse.py
│       │   └── system.py
│       │
│       ├── plugins/
│       │   ├── base.py
│       │   ├── loader.py
│       │   └── registry.py
│       │
│       ├── integrations/
│       │   ├── spotify/
│       │   ├── browser/
│       │   └── filesystem/
│       │
│       ├── config/
│       │   ├── loader.py
│       │   ├── schema.py
│       │   └── defaults.py
│       │
│       ├── ui/
│       │   ├── tray.py
│       │   ├── settings.py
│       │   └── status.py
│       │
│       ├── security/
│       │   └── permissions.py
│       │
│       └── utils/
│           ├── paths.py
│           ├── process.py
│           └── strings.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── models/
│   └── README.md
│
├── plugins/
│   └── README.md
│
└── installer/
    └── README.md
```

This structure may be adjusted if implementation experience demonstrates a better separation, but the architectural boundaries MUST remain.

---

# 5. TECHNOLOGY STACK

## Runtime

Python 3.12+

Use a modern Python project manager.

Preferred:

```text
uv
```

Dependency management must be reproducible.

---

## Speech recognition

Initial engine:

```text
Vosk
```

Reason:

* offline
* free
* lightweight
* Python-compatible
* deterministic output
* supports constrained grammars
* suitable for command recognition

The speech engine MUST be abstracted behind:

```python
SpeechEngine
```

so that Vosk is replaceable later.

---

## Windows API

Use:

```text
pywin32
```

for Windows API/COM integration.

It provides Python access to Windows APIs and COM.

Use Windows APIs directly wherever practical instead of spawning shell commands.

---

## GUI

Use:

```text
PySide6
```

for the optional settings/status interface.

The main ATLAS interface should NOT be a large window.

ATLAS is primarily a tray/background application.

---

## System tray

Use the Qt system tray facilities through PySide6.

The tray application must expose:

* current state
* microphone
* speech engine
* wake state
* settings
* reload configuration
* reload plugins
* logs
* exit

---

# 6. SPEECH PIPELINE

The speech pipeline must be:

```text
Microphone
    ↓
Audio Stream
    ↓
Wake Detector
    ↓
Listening State
    ↓
Speech Recognition
    ↓
Transcript
    ↓
Normalization
    ↓
Command Parser
    ↓
Command Object
    ↓
Validation
    ↓
Dispatcher
    ↓
Action
    ↓
Feedback
```

Every stage must be independently testable.

---

# 7. MICROPHONE ARCHITECTURE

Create:

```python
class Microphone:
    def list_devices(self): ...
    def open(self, device_id): ...
    def close(self): ...
    def start(self): ...
    def stop(self): ...
```

The user must be able to choose the microphone in configuration.

Configuration:

```toml
[audio]
device = "default"
sample_rate = 16000
channels = 1
```

The actual sample rate should be selected based on the speech engine requirements.

---

# 8. WAKE WORD

Default wake phrase:

```text
atlas
```

The wake system must support:

```text
sleeping
awake
processing
executing
error
```

Example:

```text
ATLAS asleep

User:
"Atlas"

ATLAS:
wake

User:
"Open Brave"

ATLAS:
execute

ATLAS:
return to asleep
```

Wake detection must not require a cloud service.

The wake subsystem MUST be abstracted:

```python
class WakeDetector:
    def start(self): ...
    def stop(self): ...
    def process_audio(self, audio): ...
```

The implementation can initially use constrained offline speech recognition rather than introducing a separate neural wake-word product.

---

# 9. COMMAND RECOGNITION

Speech recognition should support two modes.

## Mode A — wake detection

Only recognize the wake phrase.

Example grammar:

```text
atlas
```

## Mode B — command recognition

Once awake, recognize the available command vocabulary.

The system should avoid unrestricted dictation when possible.

This improves reliability.

---

# 10. COMMAND PARSER

The parser is the heart of ATLAS.

It must NEVER execute arbitrary text.

Input:

```text
"move brave to monitor two"
```

Output:

```python
MoveWindowCommand(
    application="brave",
    monitor=2
)
```

The parser must perform:

1. normalization
2. alias expansion
3. intent matching
4. entity extraction
5. validation
6. command construction

---

# 11. NORMALIZATION

Normalize speech before parsing.

Examples:

```text
"Monitor two"
→
"monitor 2"

"V S code"
→
"vs code"

"volume fifty"
→
"volume 50"
```

Normalization MUST NOT change semantic meaning.

---

# 12. ALIAS SYSTEM

Applications should have aliases.

Example:

```toml
[applications.brave]
aliases = ["brave", "brave browser"]

[applications.vscode]
aliases = ["vs code", "visual studio code", "code"]

[applications.spotify]
aliases = ["spotify"]
```

The user should eventually be able to modify aliases without changing Python code.

---

# 13. COMMAND MODEL

Every command must implement a common interface.

Example:

```python
class Command(ABC):

    @abstractmethod
    def validate(self) -> ValidationResult:
        ...

    @abstractmethod
    def execute(self, context: CommandContext) -> CommandResult:
        ...

    @abstractmethod
    def describe(self) -> str:
        ...
```

Commands should be data-driven where practical.

---

# 14. COMMAND REGISTRY

Create a central registry:

```python
CommandRegistry
```

Plugins register commands.

Example:

```python
registry.register(OpenApplicationCommand)
registry.register(CloseApplicationCommand)
registry.register(MoveWindowCommand)
registry.register(MaximizeWindowCommand)
```

The parser queries the registry.

This prevents a giant:

```python
if command == ...
elif command == ...
elif command == ...
```

file.

---

# 15. COMMAND CATEGORIES

ATLAS should eventually support:

```text
APPLICATION
WINDOW
MONITOR
MEDIA
AUDIO
FILESYSTEM
BROWSER
KEYBOARD
MOUSE
SYSTEM
SPOTIFY
CUSTOM
```

---

# 16. PHASE 1 COMMANDS

Only establish the interfaces during Phase 1.

Do not attempt to implement the entire command library yet.

Create placeholder/test commands:

```text
atlas status
atlas test
atlas help
```

These may be invoked internally or through a developer console.

---

# 17. WINDOWS ARCHITECTURE

Create a dedicated Windows abstraction.

```python
class WindowManager:
    list_windows()
    find_window()
    focus_window()
    move_window()
    resize_window()
    maximize_window()
    minimize_window()
    restore_window()
    close_window()
```

Never let commands directly manipulate Win32 APIs.

Instead:

```text
Command
   ↓
WindowManager
   ↓
Win32 implementation
```

This keeps commands platform-independent.

---

# 18. APPLICATION MANAGER

Create:

```python
ApplicationManager
```

Responsibilities:

* locate applications
* launch applications
* terminate applications
* detect running applications
* map spoken aliases to executables
* determine application windows

Example:

```text
"open brave"
```

becomes:

```python
ApplicationManager.launch("brave")
```

---

# 19. APPLICATION CONFIGURATION

Applications should be configurable.

Example:

```toml
[applications.brave]
executable = "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
aliases = ["brave", "brave browser"]

[applications.vscode]
executable = "..."
aliases = ["vs code", "visual studio code", "code"]
```

Where possible, ATLAS should automatically locate applications rather than requiring paths.

---

# 20. MONITOR MANAGER

Create:

```python
MonitorManager
```

Capabilities:

```text
list monitors
get primary monitor
get monitor by number
get monitor bounds
get monitor work area
```

Example:

```text
"move brave to monitor two"
```

must:

1. identify Brave window
2. identify monitor 2
3. calculate destination work area
4. move window
5. optionally preserve window size
6. focus the moved window

---

# 21. WINDOW COMMANDS

Production command set:

```text
open <application>

close <application>

focus <application>

switch to <application>

minimize <application>

maximize <application>

restore <application>

move <application> to monitor <number>

put <application> on monitor <number>

resize <application> to <width> by <height>

move <application> left

move <application> right

move <application> up

move <application> down
```

Aliases should map naturally to the same command.

---

# 22. SYSTEM COMMANDS

Eventually support:

```text
mute

unmute

volume up

volume down

set volume to 50

lock computer

sleep computer

shutdown computer

restart computer

open settings

open task manager

take screenshot
```

Destructive commands require confirmation.

For example:

```text
"shutdown computer"
```

ATLAS responds:

```text
"Confirm shutdown."
```

User:

```text
"confirm"
```

Only then execute.

Configuration may allow the user to disable confirmations.

---

# 23. FILESYSTEM COMMANDS

Support:

```text
open downloads

open documents

open desktop

open pictures

open projects

open <configured folder>
```

Configuration:

```toml
[folders]
projects = "D:\\Projects"
downloads = "C:\\Users\\Yassine\\Downloads"
```

Never allow arbitrary shell execution from voice input.

---

# 24. KEYBOARD CONTROL

Create:

```python
KeyboardController
```

Support:

```text
press enter
press escape
press tab
press space
press control c
press control v
press alt tab
press windows d
```

Support key aliases.

Example:

```text
control
ctrl
```

must map to the same key.

---

# 25. MOUSE CONTROL

Create:

```python
MouseController
```

Potential commands:

```text
click
double click
right click
move mouse left
move mouse right
scroll up
scroll down
```

Absolute coordinate voice commands should NOT be part of the initial release.

---

# 26. BROWSER CONTROL

ATLAS should not initially depend on browser extensions.

Basic functionality:

```text
open brave
new tab
close tab
next tab
previous tab
refresh
go back
go forward
focus address bar
search <query>
```

For generic web search:

```text
"search for latest Jay-Z song"
```

ATLAS may open the configured search engine.

Example:

```text
https://www.google.com/search?q=...
```

or another configured engine.

Do not scrape websites unnecessarily.

---

# 27. SPOTIFY INTEGRATION

Spotify should be implemented as an optional plugin.

The plugin must NOT be required for ATLAS core functionality.

Spotify currently provides a Web API for searching catalog content and controlling playback. The API requires authorization, and Spotify states that Web API usage requires a Premium account.

The Spotify plugin should support:

```text
open spotify

play

pause

resume

next song

previous song

volume up

volume down

search spotify for <query>

play <artist>

play <song>

play playlist <playlist>

open playlist <playlist>
```

The plugin must use official Spotify APIs where possible.

Do not attempt to circumvent Spotify authentication.

Do not download Spotify audio.

Do not scrape Spotify's internal APIs.

Spotify integration must be disabled cleanly if authentication is unavailable.

---

# 28. COMMAND CONFIDENCE

Because there is no LLM, command confidence must be handled deterministically.

Every parser match receives a score based on:

* exact phrase
* alias match
* token match
* entity match
* grammar match

Example:

```text
"move brave to monitor two"
```

Exact grammar:

```text
move + application + to + monitor + number
```

→ high confidence

Ambiguous:

```text
"move brave"
```

→ insufficient information

ATLAS must NOT guess.

It should respond:

```text
"Which monitor?"
```

---

# 29. CLARIFICATION SYSTEM

ATLAS must support multi-turn deterministic clarification.

Example:

```text
User:
"Move Brave."

ATLAS:
"Which monitor?"

User:
"Two."

ATLAS:
"Done."
```

This is NOT AI.

It is a finite state machine.

Example:

```text
STATE:
WAITING

COMMAND:
MoveWindow

MISSING:
monitor

WAIT FOR:
monitor_number
```

---

# 30. CONTEXT

ATLAS may maintain small amounts of deterministic context.

Example:

```text
User:
"Open Brave."

ATLAS:
"Brave opened."

User:
"Move it to monitor two."

```

"It" refers to the last successfully opened/controlled application.

Context should be explicit:

```python
ContextState:
    last_application
    last_window
    last_command
    last_entity
```

Context must expire after a configurable period.

Do not implement semantic reasoning.

---

# 31. FEEDBACK

ATLAS needs clear feedback.

Primary feedback mechanisms:

1. sound
2. tray icon
3. optional text notification
4. optional voice response

Voice responses should initially use a local TTS engine.

Do not require cloud TTS.

Example:

```text
User:
"Open VS Code."

ATLAS:
"Opening VS Code."
```

Voice feedback should be configurable.

---

# 32. TEXT-TO-SPEECH

Create:

```python
TTSProvider
```

with an interface:

```python
speak(text)
stop()
```

The provider must be replaceable.

The application should work perfectly with TTS disabled.

---

# 33. STATE MACHINE

ATLAS state machine:

```text
SLEEPING
    ↓
WAKE_DETECTED
    ↓
LISTENING
    ↓
RECOGNIZING
    ↓
PARSING
    ↓
VALIDATING
    ↓
EXECUTING
    ↓
FEEDBACK
    ↓
SLEEPING
```

Error path:

```text
ANY STATE
    ↓
ERROR
    ↓
RECOVERY
    ↓
SLEEPING
```

No uncaught exception should kill the background process.

---

# 34. TRAY APPLICATION

ATLAS should normally run as a background application.

Tray menu:

```text
ATLAS
──────────────
Status: Listening
Microphone: USB Audio Device
Speech: Vosk
Wake word: Atlas
──────────────
Enable voice
Disable voice
Test microphone
Test speech
──────────────
Commands
Plugins
Settings
Logs
──────────────
Reload
Restart
Exit
```

---

# 35. SETTINGS

Settings must be persisted.

Possible configuration file:

```text
%APPDATA%\Atlas\config.toml
```

Configuration categories:

```text
audio
speech
wake
tts
applications
folders
commands
plugins
appearance
logging
security
startup
```

Never hard-code user-specific paths.

---

# 36. LOGGING

Logging is mandatory.

Use structured logging.

Levels:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

Example:

```text
2026-09-20 19:00:31 INFO  Wake word detected
2026-09-20 19:00:32 INFO  Transcript: "open brave"
2026-09-20 19:00:32 INFO  Parsed command: OpenApplication(brave)
2026-09-20 19:00:32 INFO  Executing command
2026-09-20 19:00:33 INFO  Command completed
```

Logs must NEVER contain:

* passwords
* OAuth tokens
* client secrets
* API keys
* personal authentication information

---

# 37. DIAGNOSTICS

ATLAS must have a diagnostic mode.

Example:

```text
atlas --diagnose
```

It should test:

```text
Python
dependencies
microphone
audio stream
speech engine
speech model
wake detector
Windows API
monitor detection
application discovery
configuration
plugin loading
TTS
Spotify authentication
```

Output:

```text
[PASS] Python
[PASS] Microphone
[PASS] Speech engine
[PASS] Wake detector
[PASS] Windows API
[PASS] Monitor detection
[PASS] Plugin loader
[WARN] Spotify not authenticated
```

---

# 38. TESTING

Testing is mandatory.

## Unit tests

Test:

* parser
* normalization
* alias matching
* command registry
* entities
* configuration
* state machine
* monitor calculations
* command validation

## Integration tests

Test:

* microphone pipeline
* speech engine
* command dispatcher
* Windows application manager
* window manager
* plugin loader

## End-to-end tests

Example:

```text
input transcript:
"open brave"

expected:
Brave launch action
```

Do NOT require actual voice hardware for normal unit tests.

Speech recognition must be mockable.

---

# 39. COMMAND TEST FIXTURES

Every command should have fixtures.

Example:

```json
{
    "input": "move brave to monitor two",
    "expected_command": "move_window",
    "application": "brave",
    "monitor": 2
}
```

Also:

```text
move brave to monitor 2
put brave on monitor two
send brave to screen two
move brave onto display two
```

All should resolve to the same command where grammar rules explicitly support them.

---

# 40. SECURITY

Voice-controlled computer software can be dangerous.

ATLAS must treat command execution as privileged automation.

Never implement:

```text
"run this arbitrary command"
```

as:

```python
subprocess.run(user_input)
```

NEVER.

There must be a strict command registry.

Only registered actions can execute.

---

# 41. DANGEROUS COMMANDS

Commands requiring confirmation:

```text
shutdown
restart
delete
format
terminate important process
logout
factory reset
```

Potentially dangerous commands should not exist in the initial version unless explicitly implemented and tested.

---

# 42. PROCESS MANAGEMENT

ATLAS may eventually support:

```text
open task manager

close Discord

restart Spotify
```

But process termination must be controlled.

Never allow:

```text
"kill <arbitrary process name>"
```

without validation.

---

# 43. PLUGIN SYSTEM

Plugins are a major architectural requirement.

Each plugin should expose:

```python
class AtlasPlugin:

    name: str

    def initialize(self, context):
        ...

    def register_commands(self, registry):
        ...

    def shutdown(self):
        ...
```

Example:

```text
plugins/
    spotify/
    browser/
    discord/
    vscode/
```

A plugin may provide:

* commands
* application definitions
* integrations
* event handlers
* configuration
* UI settings

---

# 44. PLUGIN ISOLATION

A broken plugin must NOT crash ATLAS.

Plugin loading:

```text
discover
↓
validate
↓
load
↓
initialize
↓
register
```

If initialization fails:

```text
Plugin disabled:
Spotify
Reason:
authentication unavailable
```

ATLAS continues running.

---

# 45. CUSTOM COMMANDS

Eventually users should be able to define commands.

Example:

```toml
[[commands]]
name = "work mode"
actions = [
    "open vscode",
    "open brave",
    "move vscode to monitor 1",
    "move brave to monitor 2"
]
```

This creates deterministic macros.

No AI required.

---

# 46. MACRO ENGINE

The macro engine should support:

```text
command
delay
application launch
window movement
keyboard action
volume action
```

Example:

```text
"start work"

→ open VS Code
→ open Brave
→ move VS Code to monitor 1
→ move Brave to monitor 2
→ set volume to 30
```

Macros should be stored in configuration.

---

# 47. PHASE 2 — FUNCTIONAL IMPLEMENTATION

Phase 2 begins only when Phase 1 architecture is stable.

Objective:

Make ATLAS genuinely usable.

Implement:

## Audio

* microphone selection
* audio streaming
* device detection
* error handling

## Speech

* Vosk integration
* offline models
* recognition lifecycle
* grammar restriction
* partial/final results

## Wake

* Atlas wake phrase
* sleep state
* listening state
* timeout

## Commands

Implement:

* open application
* close application
* focus application
* switch application
* minimize
* maximize
* restore
* move to monitor
* volume
* mute
* keyboard
* browser
* filesystem

## Windows

Implement real Win32 functionality.

## Tray

Implement:

* status
* enable/disable
* microphone selection
* settings
* diagnostics
* logs
* reload

---

# 48. PHASE 2 ACCEPTANCE TEST

ATLAS must be able to perform all of these:

```text
"Atlas"

"Open Brave"

"Open VS Code"

"Switch to Brave"

"Switch to VS Code"

"Minimize Brave"

"Maximize VS Code"

"Move Brave to monitor two"

"Move VS Code to monitor one"

"Open Downloads"

"Open Projects"

"Set volume to 30"

"Mute"

"Unmute"

"Press control c"

"Press control v"

"Open a new tab"

"Close tab"

"Refresh"
```

All commands must execute without internet access.

---

# 49. PHASE 3 — PRODUCTION

Phase 3 means ATLAS is no longer merely a developer project.

It must become a distributable Windows application.

---

# 50. PRODUCTION REQUIREMENTS

ATLAS must have:

* production executable
* installer
* uninstaller
* startup option
* persistent configuration
* logging
* crash recovery
* diagnostics
* settings UI
* plugin system
* documentation
* version information
* clean shutdown
* automatic startup option
* model installation
* migration support
* configuration backup
* update architecture

---

# 51. PACKAGING

Preferred:

```text
PyInstaller
```

or another appropriate Python-to-Windows packaging system if technical testing demonstrates a better solution.

Final application should not require the user to install Python manually.

Expected user experience:

```text
Download Atlas Installer
        ↓
Install
        ↓
Choose microphone
        ↓
Download/install speech model
        ↓
Choose "Start with Windows"
        ↓
Finish
        ↓
ATLAS tray icon
        ↓
"Atlas"
```

---

# 52. INSTALLER

Installer should support:

```text
Install location
Start with Windows
Desktop shortcut
Start menu shortcut
Microphone setup
Speech model installation
Configuration location
```

Uninstaller must cleanly remove:

* application files
* shortcuts
* startup registration
* optional user configuration if explicitly selected

Never silently delete user configuration.

---

# 53. FIRST-RUN EXPERIENCE

First launch:

```text
Welcome to ATLAS.

Let's configure your voice assistant.
```

Step 1:

```text
Select microphone.
```

Step 2:

```text
Test microphone.
```

Step 3:

```text
Install speech model.
```

Step 4:

```text
Say:
"Atlas"
```

Step 5:

```text
Say:
"Open Notepad"
```

Step 6:

```text
Success.
ATLAS is ready.
```

---

# 54. SETTINGS UI

Settings should expose:

## General

* start with Windows
* launch minimized
* enable voice
* wake phrase

## Audio

* microphone
* sensitivity
* sample rate

## Speech

* engine
* model
* language

## Voice

* TTS enabled
* voice
* response volume

## Commands

* command aliases
* confirmations

## Applications

* application aliases
* executable paths

## Folders

* custom folder aliases

## Plugins

* enabled/disabled
* configuration

## Diagnostics

* microphone test
* speech test
* logs
* system information

---

# 55. PERFORMANCE TARGETS

ATLAS should be lightweight.

Target:

```text
Idle CPU:
< 3% average

Idle RAM:
< 250 MB

Wake response:
< 1 second where hardware permits

Command execution:
near-immediate after recognition
```

Do not optimize prematurely.

Measure before optimizing.

---

# 56. FAILURE HANDLING

ATLAS must survive:

* microphone disconnect
* microphone reconnect
* speech engine failure
* malformed transcript
* invalid command
* application not installed
* application already closed
* monitor disconnected
* Spotify authentication failure
* plugin crash
* TTS failure
* configuration corruption

Example:

```text
User:
"Open Photoshop"

Photoshop isn't installed.

ATLAS:
"Photoshop was not found."
```

It must NOT crash.

---

# 57. OFFLINE GUARANTEE

With no internet connection:

```text
wake word       YES
speech          YES
commands        YES
Windows control YES
applications    YES
window control  YES
filesystem      YES
system control  YES
macros          YES
Spotify search  NO
web search      NO
online updates  NO
```

ATLAS should clearly distinguish offline and online capabilities.

---

# 58. ONLINE INTEGRATIONS

Online plugins must be isolated.

Example:

```text
core
├── offline functionality
│
└── integrations
    ├── spotify
    ├── web
    └── future services
```

The core must never depend on these.

---

# 59. SPOTIFY PRODUCTION DESIGN

Spotify should be optional.

The plugin should support OAuth.

Credentials/tokens must be stored securely.

Never put secrets in:

```text
Git
logs
configuration committed to repository
source code
```

The Spotify Web API provides search and playback-control endpoints, but current Spotify documentation states that Web API usage requires Premium; playback commands use OAuth scopes such as `user-modify-playback-state`.

Therefore ATLAS should treat Spotify as:

```text
Optional integration
```

not a core requirement.

---

# 60. WEB SEARCH

ATLAS should eventually support:

```text
"search the web for ..."
```

Implementation:

1. parse command
2. encode query
3. open configured browser
4. navigate to configured search engine

No AI search required.

Example:

```text
"search the web for the latest Jay-Z song"
```

becomes:

```text
OPEN_BROWSER_SEARCH(
    query="latest Jay-Z song"
)
```

---

# 61. COMMAND DISCOVERY

ATLAS should support:

```text
"what can you do?"

"help"

"what commands do I have?"
```

It should display or speak categories.

Example:

```text
Applications
Windows
Media
Browser
System
Files
Spotify
Macros
```

---

# 62. UNKNOWN COMMANDS

If ATLAS doesn't understand:

```text
"I didn't understand that command."
```

It must NOT invent an action.

Optional diagnostic mode:

```text
Unrecognized:
"move the browser thing to screen two"

Closest commands:
move <application> to monitor <number>
```

This is deterministic fuzzy matching.

---

# 63. FUZZY MATCHING

Fuzzy matching may be used for:

* application names
* aliases
* command phrases
* folder names

But fuzzy matching MUST NOT bypass safety validation.

Example:

```text
"spotifyy"
```

may match:

```text
spotify
```

But:

```text
"shutdown"
```

must not fuzzy-match some unrelated destructive command.

---

# 64. CONFIGURATION MIGRATION

Configuration must contain a version:

```toml
config_version = 1
```

When configuration schema changes:

```text
version 1
    ↓
migration
    ↓
version 2
```

Never silently discard old configuration.

---

# 65. UPDATE ARCHITECTURE

ATLAS should have an update mechanism architecture even if automatic updates are not implemented initially.

Components:

```text
current_version
latest_version
update_available
download
verify
install
rollback
```

Do not implement automatic downloading until update integrity is designed.

---

# 66. CRASH RECOVERY

If ATLAS crashes:

* log crash
* attempt clean shutdown
* optionally restart
* do not enter infinite restart loop

Use:

```text
max restart attempts
cooldown
crash counter
```

---

# 67. TELEMETRY

Default:

```text
NONE
```

ATLAS must not collect:

* voice recordings
* transcripts
* usage data
* personal files
* application activity
* browsing history

unless the user explicitly enables a local diagnostic feature.

Even diagnostics should remain local by default.

---

# 68. PRIVACY

Microphone access is continuous while ATLAS is active.

Therefore the application must make its microphone state obvious.

Tray states:

```text
SLEEPING
LISTENING
PROCESSING
DISABLED
ERROR
```

The user must always know whether ATLAS is listening.

---

# 69. AUDIO RECORDINGS

Do not persist microphone recordings by default.

Temporary audio buffers should exist only in memory.

Debug recording:

```text
disabled by default
```

If enabled:

```text
explicit user setting
```

Provide a clear location and delete function.

---

# 70. DEVELOPMENT CLI

Provide:

```text
atlas
atlas --help
atlas --version
atlas --diagnose
atlas --test-microphone
atlas --test-speech
atlas --list-devices
atlas --list-monitors
atlas --list-windows
atlas --list-plugins
atlas --reload
```

This is extremely important for debugging.

---

# 71. DEVELOPER MODE

Developer mode should provide:

```text
raw transcript
normalized transcript
matched grammar
parsed command
command arguments
execution result
execution time
```

Example:

```text
RAW:
move brave to screen too

NORMALIZED:
move brave to monitor 2

MATCH:
move_window

ARGS:
application=brave
monitor=2

RESULT:
success
```

---

# 72. DOCUMENTATION REQUIREMENTS

The repository must contain:

```text
README.md
ARCHITECTURE.md
COMMANDS.md
PLUGIN_DEVELOPMENT.md
CONFIGURATION.md
TROUBLESHOOTING.md
SECURITY.md
DEVELOPMENT.md
RELEASE.md
```

Documentation must be kept synchronized with implementation.

---

# 73. CODE QUALITY

Use:

```text
ruff
pytest
mypy
```

where appropriate.

Formatting/linting must be automated.

No:

```python
except:
    pass
```

No unexplained global state.

No circular imports.

No enormous modules.

No duplicated Windows API logic.

No command implementation directly inside UI code.

---

# 74. TYPE SAFETY

Use type hints throughout.

Prefer:

```python
@dataclass(frozen=True)
class MoveWindowCommand:
    application: str
    monitor: int
```

over unstructured dictionaries when practical.

---

# 75. DEPENDENCY POLICY

Every dependency must have a reason.

Before adding a package, ask:

1. Can Python do this?
2. Can Windows API do this?
3. Is there already a project dependency that provides it?
4. Is the package maintained?
5. Is its license acceptable?
6. Does it increase attack surface?
7. Does it significantly increase application size?

Do not add dependencies merely for convenience.

---

# 76. LICENSE POLICY

Before release, audit every dependency.

Create:

```text
docs/licenses.md
```

containing:

* dependency
* version
* license
* source
* distribution obligations

---

# 77. PHASE 3 FINAL FEATURE SET

Phase 3 is considered complete only when ATLAS can provide all of the following.

## Voice

* wake phrase
* offline recognition
* configurable microphone
* sleep/wake state
* timeout
* recognition feedback

## Applications

* open
* close
* focus
* switch
* restart where supported
* aliases

## Windows

* maximize
* minimize
* restore
* move
* resize
* monitor selection
* focus

## System

* volume
* mute
* keyboard
* screenshot
* lock
* safe power actions

## Browser

* open
* new tab
* close tab
* refresh
* navigation
* search

## Files

* known folders
* configured folders
* open folders/files

## Media

* play
* pause
* next
* previous
* volume

## Spotify

* search
* playback control
* playlists
* optional authentication

## Macros

* custom commands
* sequences
* delays
* multiple applications

## Infrastructure

* settings
* diagnostics
* logs
* plugins
* installer
* updater architecture
* crash recovery
* documentation

---

# 78. DEFINITION OF DONE

ATLAS is DONE only if:

### Installation

A clean Windows machine can install ATLAS without manually installing Python.

### Startup

ATLAS can start with Windows.

### Microphone

The user can select and test a microphone.

### Wake

The user can say:

```text
Atlas
```

and enter listening mode.

### Recognition

Speech is converted locally into text.

### Parsing

Known commands are parsed deterministically.

### Execution

Commands execute against Windows.

### Feedback

The user receives clear feedback.

### Safety

Unknown commands cannot execute arbitrary code.

### Reliability

A failed command does not crash ATLAS.

### Offline

Core functionality works without internet.

### Configuration

Settings persist.

### Plugins

A plugin can be installed/disabled without breaking core functionality.

### Diagnostics

A developer can determine why the system isn't working without guessing.

### Production

The application can be installed, used, uninstalled, and reinstalled cleanly.

---

# 79. IMPLEMENTATION ORDER

Claude Code MUST follow this order.

## Phase 1

```text
1. Initialize repository
2. Configure Python environment
3. Configure dependency management
4. Create package structure
5. Create logging
6. Create configuration
7. Create application lifecycle
8. Create state machine
9. Create command interfaces
10. Create command registry
11. Create plugin interfaces
12. Create Windows abstraction interfaces
13. Create speech interfaces
14. Create audio interfaces
15. Create tray skeleton
16. Create test infrastructure
17. Create documentation
18. Verify architecture
```

STOP.

Do not jump ahead.

---

## Phase 2

```text
1. Implement microphone
2. Implement Vosk
3. Implement wake detection
4. Implement parser
5. Implement command dispatcher
6. Implement application manager
7. Implement window manager
8. Implement monitor manager
9. Implement keyboard manager
10. Implement system manager
11. Implement browser commands
12. Implement filesystem commands
13. Implement tray UI
14. Implement diagnostics
15. Implement tests
16. Implement Spotify plugin
17. Implement macro engine
```

Then perform full integration testing.

---

## Phase 3

```text
1. Performance profiling
2. Reliability testing
3. Security audit
4. Dependency audit
5. Configuration migration
6. Crash recovery
7. Production logging
8. Installer
9. Uninstaller
10. Startup integration
11. Documentation finalization
12. Release build
13. Clean-machine testing
14. Regression testing
15. Final acceptance testing
```

---

# 80. CLAUDE CODE OPERATING RULES

Claude Code MUST:

### DO

* inspect the existing repository before modifying anything
* maintain architecture boundaries
* write tests with new functionality
* run tests after significant changes
* run linting
* keep documentation updated
* explain architectural decisions in commits/docs
* use small incremental changes
* preserve working functionality
* validate Windows-specific behavior

### DO NOT

* rewrite the whole project unnecessarily
* add an LLM
* add cloud AI
* add paid APIs
* hard-code user paths
* hard-code credentials
* execute arbitrary shell commands from voice input
* store microphone recordings by default
* silently collect telemetry
* create a giant monolithic `assistant.py`
* put all commands into one file
* hide failures
* swallow exceptions
* skip tests because functionality "looks simple"

---

# 81. GIT STRATEGY

Recommended branches:

```text
main
develop
feature/*
fix/*
```

Commits should be small and meaningful.

Examples:

```text
feat: add command registry
feat: implement offline speech engine
feat: add window manager
feat: add monitor movement
fix: recover from microphone disconnect
test: add parser fixtures
docs: document plugin architecture
```

---

# 82. MILESTONE SYSTEM

Each phase must have explicit milestones.

## Phase 1 milestones

```text
P1.1 Repository
P1.2 Core architecture
P1.3 Configuration
P1.4 Logging
P1.5 Command system
P1.6 Plugin system
P1.7 Windows abstraction
P1.8 Speech abstraction
P1.9 UI skeleton
P1.10 Testing foundation
```

## Phase 2 milestones

```text
P2.1 Microphone
P2.2 Speech recognition
P2.3 Wake system
P2.4 Parser
P2.5 Windows control
P2.6 Applications
P2.7 Browser
P2.8 Files
P2.9 System
P2.10 Spotify
P2.11 Macros
```

## Phase 3 milestones

```text
P3.1 Stability
P3.2 Security
P3.3 Performance
P3.4 Installer
P3.5 Uninstaller
P3.6 Startup
P3.7 Diagnostics
P3.8 Documentation
P3.9 Clean-machine test
P3.10 Release
```

---

# 83. FINAL ARCHITECTURE

The final system should conceptually look like this:

```text
                         ┌─────────────────┐
                         │    MICROPHONE   │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  AUDIO MANAGER  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  WAKE DETECTOR  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ SPEECH ENGINE   │
                         │     VOSK        │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ NORMALIZER      │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ COMMAND PARSER  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ COMMAND         │
                         │ REGISTRY        │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ VALIDATOR       │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ DISPATCHER      │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼────────────────────┐
              │                   │                    │
              ▼                   ▼                    ▼
       ┌────────────┐      ┌────────────┐       ┌────────────┐
       │ Windows    │      │ Plugins    │       │ Macros     │
       │ Controller │      │            │       │            │
       └────────────┘      └────────────┘       └────────────┘
              │                   │                    │
              ▼                   ▼                    ▼
       ┌────────────┐      ┌────────────┐       ┌────────────┐
       │ Win32 API  │      │ Spotify    │       │ Sequences  │
       │            │      │ Browser    │       │            │
       │            │      │ Future     │       │            │
       └────────────┘      └────────────┘       └────────────┘
```

---

# 84. THE MOST IMPORTANT ARCHITECTURAL RULE

Do NOT build ATLAS as:

```text
microphone → giant Python file → actions
```

Build it as:

```text
INPUT
 ↓
INTERPRETATION
 ↓
COMMAND
 ↓
VALIDATION
 ↓
EXECUTION
```

This distinction is what will allow ATLAS to grow from a simple voice-control utility into a serious desktop automation platform.

---

# 85. FIRST IMPLEMENTATION TASK

When beginning work, Claude Code should NOT immediately write hundreds of files.

First:

1. Inspect repository.
2. Confirm Windows environment.
3. Confirm Python version.
4. Confirm package manager.
5. Create repository structure.
6. Create `pyproject.toml`.
7. Create core interfaces.
8. Create a minimal executable.
9. Create tests proving the architecture works.
10. Run the application.
11. Run tests.
12. Report Phase 1 completion.

Only after Phase 1 is validated should implementation proceed into Phase 2.

---

# 86. FINAL PRINCIPLE

ATLAS should feel like a powerful computer assistant while remaining fundamentally simple underneath.

The system should not need to "think."

It needs to:

```text
HEAR
↓
RECOGNIZE
↓
MATCH
↓
VALIDATE
↓
EXECUTE
```

The intelligence of ATLAS comes from the quality of its command language, application integrations, context system, deterministic parser, and Windows automation layer — not from an AI model.

The ultimate goal is:

> **"Atlas"**

followed by almost anything the user has explicitly taught the system to do.

Fast.

Local.

Private.

Free.

Predictable.

And completely under the user's control.

---

# END OF SPECIFICATION
