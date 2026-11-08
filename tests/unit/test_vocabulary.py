from tests.fixtures.fakes import (
    FakeApplicationManager,
    FakeKeyboardController,
    FakeMonitorManager,
    FakeMouseController,
    FakeSystemController,
    FakeWindowManager,
)

from atlas.application.app import Application
from atlas.config.schema import ApplicationEntry
from atlas.speech.vocabulary import _FOLLOW_UPS, command_vocabulary


def make_app() -> Application:
    window_manager = FakeWindowManager()
    app = Application(
        window_manager=window_manager,
        monitor_manager=FakeMonitorManager(),
        keyboard_controller=FakeKeyboardController(),
        mouse_controller=FakeMouseController(),
        system_controller=FakeSystemController(),
        application_manager=FakeApplicationManager(window_manager),
    )
    app.bootstrap()
    app.config.applications["brave"] = ApplicationEntry(aliases=["brave", "brave browser"])
    return app


def test_vocabulary_covers_apps_numbers_keys_and_follow_ups():
    app = make_app()
    vocab = set(command_vocabulary(app.parser, app.config))
    for phrase in (
        "open brave",
        "switch to brave browser",
        "close brave",
        "move brave to monitor two",
        "move brave",
        "set volume to fifty",
        "press control c",
        "press enter",
        "mute",
        "new tab",
        "open downloads",
        "confirm",
        "monitor two",
    ):
        assert phrase in vocab, phrase
    assert not any("{" in phrase for phrase in vocab)  # free-text templates are left out


def test_every_vocabulary_phrase_parses():
    """Whatever the recognizer can hear, the parser must understand."""
    app = make_app()
    for phrase in command_vocabulary(app.parser, app.config):
        if phrase in _FOLLOW_UPS:
            continue
        result = app.parser.parse(phrase)
        assert result.ok or result.needs_clarification, phrase
