"""System tray shell (Atlas.md section 34). The tray owns no business logic
- it only presents state and forwards user actions to callbacks supplied by
the caller (normally atlas.application.app.Application)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from atlas.ui.status import status_text


class TrayApplication:
    def __init__(
        self,
        *,
        on_enable_voice: Callable[[], None] | None = None,
        on_disable_voice: Callable[[], None] | None = None,
        on_test_microphone: Callable[[], None] | None = None,
        on_test_speech: Callable[[], None] | None = None,
        on_open_settings: Callable[[], None] | None = None,
        on_open_logs: Callable[[], None] | None = None,
        on_reload: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
    ) -> None:
        self._qt_app = QApplication.instance() or QApplication([])
        self._tray = QSystemTrayIcon(QIcon())
        self._menu = QMenu()
        self._actions: list[QAction] = []

        self._status_action = QAction(status_text("SLEEPING"))
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)
        self._menu.addSeparator()

        self._add_action("Enable voice", on_enable_voice)
        self._add_action("Disable voice", on_disable_voice)
        self._add_action("Test microphone", on_test_microphone)
        self._add_action("Test speech", on_test_speech)
        self._menu.addSeparator()
        self._add_action("Settings", on_open_settings)
        self._add_action("Logs", on_open_logs)
        self._menu.addSeparator()
        self._add_action("Reload", on_reload)
        self._add_action("Exit", on_exit or self._qt_app.quit)

        self._tray.setContextMenu(self._menu)
        self._tray.setToolTip("ATLAS")

    def _add_action(self, label: str, callback: Callable[[], None] | None) -> None:
        action = QAction(label)
        if callback is not None:
            action.triggered.connect(callback)
        self._menu.addAction(action)
        self._actions.append(action)

    def set_status(self, state_name: str) -> None:
        self._status_action.setText(status_text(state_name))

    def show(self) -> None:
        self._tray.show()

    def run(self) -> int:
        self.show()
        return self._qt_app.exec()
