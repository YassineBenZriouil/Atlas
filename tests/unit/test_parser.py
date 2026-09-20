from atlas.commands.builtin import register_builtin_commands, register_builtin_grammars
from atlas.commands.parser import CommandParser
from atlas.commands.registry import CommandRegistry


def make_parser() -> CommandParser:
    registry = CommandRegistry()
    register_builtin_commands(registry)
    parser = CommandParser(registry)
    register_builtin_grammars(parser)
    return parser


def test_exact_phrase_matches():
    result = make_parser().parse("atlas status")
    assert result.ok
    assert result.matched_name == "atlas_status"


def test_alias_phrase_matches():
    result = make_parser().parse("help")
    assert result.ok
    assert result.matched_name == "atlas_help"


def test_unknown_phrase_does_not_match():
    result = make_parser().parse("do something dangerous")
    assert not result.ok
    assert result.command is None
    assert result.error


def test_normalization_applied_before_matching():
    result = make_parser().parse("  ATLAS   STATUS  ")
    assert result.ok


def test_unmatched_grammar_without_registered_command():
    from atlas.commands.matcher import Grammar

    registry = CommandRegistry()
    parser = CommandParser(registry)
    parser.add_grammar(Grammar("ghost_command", ("ghost",)))
    result = parser.parse("ghost")
    assert not result.ok
    assert result.matched_name == "ghost_command"
