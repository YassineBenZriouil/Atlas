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

## Grammars (Phase 1)

Phase 1 ships exact-phrase grammars only, via `atlas.commands.matcher.Grammar`:

```python
parser.add_grammar(Grammar("atlas_status", ("atlas status", "status")))
```

Alias expansion, fuzzy matching, and entity-bound grammars (e.g.
`"move <application> to monitor <number>"`) are Phase 2 work - the
building blocks (`atlas.commands.entities.extract_monitor_number` etc.)
already exist and are unit tested, but are not yet wired into the parser.

## Built-in commands

`atlas.commands.builtin` registers three developer commands that prove the
pipeline end-to-end without touching Windows:

- `atlas status` / `status`
- `atlas test` / `test`
- `atlas help` / `help` / `what can you do`

## Categories

`CommandCategory`: `APPLICATION`, `WINDOW`, `MONITOR`, `MEDIA`, `AUDIO`,
`FILESYSTEM`, `BROWSER`, `KEYBOARD`, `MOUSE`, `SYSTEM`, `SPOTIFY`,
`DEVELOPER`, `CUSTOM`.

## Confirmation

`atlas.security.permissions.DANGEROUS_COMMAND_NAMES` lists command names
that require confirmation before `CommandDispatcher.dispatch` will execute
them (unless `confirmed=True` is passed, which the confirmation-flow layer
sets after the user says "confirm"). No dangerous command exists in Phase 1
yet - the registry is empty of them, but the gate is implemented and unit
tested so Phase 2 commands can rely on it immediately.
