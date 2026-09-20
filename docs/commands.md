# Commands

## The interface

Every command implements `atlas.commands.command.Command`:

```python
class Command(ABC):
    name: str
    category: CommandCategory

    def validate(self) -> ValidationResult: ...
    def execute(self, context: CommandContext) -> CommandResult: ...
    def describe(self) -> str: ...
```

`validate()` runs before `execute()` in `CommandDispatcher.dispatch`. A
command that can be constructed with missing/invalid data should fail
validation, not raise inside `execute()`.

## Registering a command

```python
from atlas.commands.registry import CommandRegistry

registry = CommandRegistry()
registry.register(MyCommand)
```

The parser resolves grammars to command *names*, then asks the registry for
the class and instantiates it - there is never an `if command == ...`
chain (Atlas.md section 14).

## Grammars

Exact phrases (`atlas.commands.matcher.Grammar`):

```python
parser.add_grammar(Grammar("atlas_status", ("atlas status", "status")))
```

Templated patterns with entities (`add_pattern`), tried after exact
phrases:

```python
parser.add_pattern("open_application", "open {application}", lambda g: {"application": g["application"].strip()})
```

Register more specific patterns before more general ones sharing a verb -
`"search the web for {query}"` must be tried before the catch-all
`"search {query}"`, or the generic one wins every time. See
`atlas.commands.window_commands` for a worked example with several
phrasings mapping to `move_to_monitor`.

## Built-in developer commands

`atlas.commands.builtin` registers three commands that prove the pipeline
end-to-end without touching Windows:

- `atlas status` / `status`
- `atlas test` / `test`
- `atlas help` / `help` / `what can you do`

## Implemented command set

| Category | Commands | Module |
|---|---|---|
| Application | open/close/focus (switch to)/minimize/maximize/restore `<application>` | `atlas.commands.application_commands` |
| Window | move to monitor / resize / move left/right/up/down | `atlas.commands.window_commands` |
| System | mute/unmute/volume up/down/set, lock, sleep, shutdown\*, restart\*, screenshot | `atlas.commands.system_commands` |
| Keyboard | press `<key>` [`<key>` ...] | `atlas.commands.keyboard_commands` |
| Browser | new/close/next/previous tab, refresh, back/forward, focus address bar, search, web search | `atlas.integrations.browser.commands` |
| Filesystem | open `<known or configured folder>` - folded into the "open" application command (see below) | `atlas.integrations.filesystem.folders` |

\* requires confirmation - see below.

"open X" deliberately has exactly **one** grammar covering both
applications and folders (Atlas.md sections 18 and 23 both use the verb
"open"): `OpenApplicationCommand.execute()` tries application resolution
first, then falls back to `resolve_folder()`. Two commands bound to the
identical `"open {x}"` text would leave one of them unreachable.

## Categories

`CommandCategory`: `APPLICATION`, `WINDOW`, `MONITOR`, `MEDIA`, `AUDIO`,
`FILESYSTEM`, `BROWSER`, `KEYBOARD`, `MOUSE`, `SYSTEM`, `SPOTIFY`,
`DEVELOPER`, `CUSTOM`.

## Clarification

A command family can register a "custom matcher" via
`CommandParser.add_custom_matcher` that returns a
`NeedsClarification(prompt, resolve)` instead of a `Command` when it
recognizes the verb/target but is missing something it needs (Atlas.md
sections 28-29). `Application` remembers exactly one pending
clarification and treats the *next* utterance as the answer:

```
User: "Move Brave."
ATLAS: "Which monitor?"
User: "Two."
ATLAS: "Moved brave to monitor 2"
```

See `atlas.commands.window_commands._bare_move_matcher` for the
implementation, and `tests/integration/test_confirmation_and_clarification.py`
for the abandon-on-bad-followup case.

## Confirmation

`atlas.security.permissions.DANGEROUS_COMMAND_NAMES` lists command names
that require confirmation before `CommandDispatcher.dispatch` will execute
them. `shutdown_computer` and `restart_computer` are both implemented and
gated: `Application._run_command` catches the dispatcher's
`AwaitingConfirmation`, remembers the pending command, and only actually
dispatches it if the next utterance is "confirm" (or "yes"/"confirmed"/
"do it") - anything else cancels it. This is tested with fakes so the test
suite never actually shuts a machine down
(`test_shutdown_requires_confirmation_and_never_executes_without_it`).
