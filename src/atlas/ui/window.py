"""The ATLAS window (docs/ROADMAP.md, Phase 3): a client of the background
core. Closing it only closes the window - the core, and voice, keep
running. Opening it again (`atlas` / `atlas-gui`) focuses the existing
window if one is already open."""

from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from atlas.service.client import CoreClient, connect, ensure_core
from atlas.ui.bridge import ClientProvider, CoreBridge
from atlas.ui.icon import build_icon
from atlas.ui.pages import ApplicationsPage, LivePage, LogsPage, PluginsPage, SettingsPage
from atlas.ui.theme import stylesheet

_INSTANCE_SERVER = "atlas-window"
_STATUS_TIMEOUT_MS = 6000


class MainWindow(QMainWindow):
    def __init__(self, client_provider: ClientProvider = connect, autostart: bool = True) -> None:
        super().__init__()
        self.setWindowTitle("ATLAS")
        self.setWindowIcon(build_icon("SLEEPING"))
        self.resize(980, 640)
        self.setMinimumSize(720, 480)

        self.bridge = CoreBridge(client_provider)
        self._core_pid: int | None = None
        self._starting = False

        self.live = LivePage(self.bridge, self.notify)
        self.applications = ApplicationsPage(self.bridge, self.notify)
        self.plugins = PluginsPage(self.bridge, self.notify)
        self.settings = SettingsPage(self.bridge, self.notify)
        self.logs = LogsPage(self.bridge, self.notify)
        # Every page has refresh(); Live refreshes itself on connect.
        self._pages: list[tuple[str, Any]] = [
            ("Live", self.live),
            ("Applications", self.applications),
            ("Plugins", self.plugins),
            ("Settings", self.settings),
            ("Logs", self.logs),
        ]

        root = QWidget()
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        sidebar.setFixedWidth(190)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 12)
        side.setSpacing(8)
        brand = QLabel("ATLAS")
        brand.setProperty("role", "title")
        brand.setContentsMargins(24, 18, 0, 6)
        side.addWidget(brand)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        for name, _ in self._pages:
            self.nav.addItem(name)
        side.addWidget(self.nav, 1)
        self.start_button = QPushButton("Start ATLAS")
        self.start_button.setProperty("role", "primary")
        self.start_button.clicked.connect(self.start_core)
        self.quit_button = QPushButton("Quit ATLAS")
        self.quit_button.setProperty("role", "danger")
        self.quit_button.setToolTip("Stop the background core. Voice commands stop too.")
        self.quit_button.clicked.connect(self.quit_core)
        for button in (self.start_button, self.quit_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            wrapper = QHBoxLayout()
            wrapper.setContentsMargins(12, 0, 12, 0)
            wrapper.addWidget(button)
            side.addLayout(wrapper)
        row.addWidget(sidebar)

        self.stack = QStackedWidget()
        for _, page in self._pages:
            self.stack.addWidget(page)
        row.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.nav.currentRowChanged.connect(self._show_page)
        self.nav.setCurrentRow(0)

        self.bridge.connected.connect(self._on_connected)
        self.bridge.core_event.connect(self.live.on_event)
        self._set_offline()
        self.bridge.start()
        if autostart:
            self.start_core()  # returns at once if a core is already running

    # -- core connection ----------------------------------------------------

    def _on_connected(self, client: CoreClient | None) -> None:
        if client is None:
            self._set_offline()
            return
        if client.info.pid != self._core_pid:
            # A different core process: its event ids start over.
            self.live.reset()
            self._core_pid = client.info.pid
        self._starting = False
        self.start_button.hide()
        self.quit_button.setEnabled(True)
        self.statusBar().showMessage(f"Connected to ATLAS core (pid {client.info.pid})")
        self.live.refresh()
        page = self._pages[self.stack.currentIndex()][1]
        if page is not self.live:
            page.refresh()

    def _set_offline(self) -> None:
        self.live.set_offline()
        self.quit_button.setEnabled(False)
        self.start_button.setVisible(True)
        self.start_button.setEnabled(not self._starting)
        self.start_button.setText("Starting…" if self._starting else "Start ATLAS")

    def start_core(self) -> None:
        self._starting = True
        self._set_offline()
        self.notify("Starting the ATLAS core…")

        def failed(exc: Exception) -> None:
            self._starting = False
            self._set_offline()
            self.notify(str(exc))

        self.bridge.run_in_thread(ensure_core, lambda client: None, failed)

    def quit_core(self) -> None:
        answer = QMessageBox.question(
            self,
            "Quit ATLAS?",
            "This stops the background core: voice commands stop until you start ATLAS again.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.bridge.call(
            lambda c: c.quit(),
            lambda _: self.notify("ATLAS core stopped"),
            lambda exc: self.notify(str(exc)),
        )

    # -- misc ---------------------------------------------------------------

    def _show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        page = self._pages[index][1]
        if self.bridge.client is not None and page is not self.live:
            page.refresh()

    def notify(self, message: str) -> None:
        self.statusBar().showMessage(message, _STATUS_TIMEOUT_MS)

    def bring_to_front(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        self.bridge.stop()  # the core keeps running; only the window goes away
        super().closeEvent(event)


def _focus_existing_window() -> bool:
    socket = QLocalSocket()
    socket.connectToServer(_INSTANCE_SERVER)
    if not socket.waitForConnected(300):
        return False
    socket.write(QByteArray(b"show"))
    socket.waitForBytesWritten(300)
    socket.disconnectFromServer()
    return True


def _listen_for_other_launches(window: MainWindow) -> QLocalServer:
    QLocalServer.removeServer(_INSTANCE_SERVER)  # a crashed window can leave a stale one
    server = QLocalServer(window)
    server.newConnection.connect(window.bring_to_front)
    server.listen(_INSTANCE_SERVER)
    return server


def run_window() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    assert isinstance(app, QApplication)
    if _focus_existing_window():
        return 0
    app.setApplicationName("ATLAS")
    app.setStyleSheet(stylesheet())
    window = MainWindow()
    _listen_for_other_launches(window)
    window.show()
    return app.exec()


def main() -> int:
    """`atlas-gui` entry point (no console window)."""
    return run_window()
