"""Regression test for a real bug: QSystemTrayIcon(QIcon()) - an empty
icon - renders nothing and Qt logs "No Icon set"; Windows may not show a
usable tray entry at all. Never construct the tray without a real icon.
No `.show()` here, so no tray icon actually appears during test runs.

Building a QPixmap/QPainter (what build_icon does) requires a
QApplication to already exist - without one, Qt crashes the process
rather than raising a catchable Python exception. The real app is always
safe (TrayApplication.__init__ constructs QApplication first), but a
standalone test needs this fixture to get the same guarantee."""

import pytest
from PySide6.QtWidgets import QApplication

from atlas.ui.icon import build_icon
from atlas.ui.tray import TrayApplication


@pytest.fixture(scope="module", autouse=True)
def qt_application():
    yield QApplication.instance() or QApplication([])


def test_build_icon_is_never_null():
    for state in ("SLEEPING", "LISTENING", "EXECUTING", "ERROR", "SOME_UNKNOWN_STATE"):
        assert not build_icon(state).isNull()


def test_tray_application_starts_with_a_real_icon():
    tray = TrayApplication()
    assert not tray._tray.icon().isNull()


def test_set_status_keeps_a_real_icon_and_updates_text():
    tray = TrayApplication()
    tray.set_status("EXECUTING")
    assert not tray._tray.icon().isNull()
    assert "executing" in tray._status_action.text().lower()
