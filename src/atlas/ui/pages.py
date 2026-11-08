"""The window's pages. Each talks to the core only through CoreBridge, and
re-reads the config right before saving so two pages never overwrite each
other's changes."""

from __future__ import annotations

import math
import sys
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from atlas.platform import open_path
from atlas.ui.bridge import CoreBridge
from atlas.ui.theme import COLORS, STATUS_COLORS, STATUS_TEXT

Notify = Callable[[str], None]

_SPEECH_SETTINGS_URI = "ms-settings:privacy-speech"


def _label(text: str = "", role: str = "") -> QLabel:
    label = QLabel(text)
    if role:
        label.setProperty("role", role)
    label.setWordWrap(True)
    return label


def _button(text: str, role: str = "") -> QPushButton:
    button = QPushButton(text)
    if role:
        button.setProperty("role", role)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def _panel() -> QFrame:
    frame = QFrame()
    frame.setProperty("role", "panel")
    return frame


def _page_header(title: str, subtitle: str) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(2)
    layout.addWidget(_label(title, "title"))
    layout.addWidget(_label(subtitle, "muted"))
    return layout


class StatusOrb(QWidget):
    """A colored dot for the voice state; pulses while ATLAS is listening."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(56, 56)
        self._status = "offline"
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    @property
    def status(self) -> str:
        return self._status

    def set_status(self, status: str) -> None:
        self._status = status
        if status in ("listening", "recognizing"):
            self._timer.start()
        else:
            self._timer.stop()
            self._phase = 0.0
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.12) % (2 * math.pi)
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        color = QColor(STATUS_COLORS.get(self._status, STATUS_COLORS["sleeping"]))
        if self._timer.isActive():
            halo = QColor(color)
            halo.setAlpha(int(50 + 40 * math.sin(self._phase)))
            painter.setBrush(QBrush(halo))
            painter.drawEllipse(self.rect())
        painter.setBrush(QBrush(color))
        painter.drawEllipse(self.rect().adjusted(10, 10, -10, -10))


class LivePage(QWidget):
    def __init__(self, bridge: CoreBridge, notify: Notify) -> None:
        super().__init__()
        self._bridge = bridge
        self._notify = notify
        self._pending_via = ""
        self._open_row: QTreeWidgetItem | None = None
        self._seen_ids: set[int] = set()
        self.wake_phrase = "atlas"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        state_panel = _panel()
        state_row = QHBoxLayout(state_panel)
        state_row.setContentsMargins(16, 14, 16, 14)
        state_row.setSpacing(14)
        self.orb = StatusOrb()
        state_row.addWidget(self.orb)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.state_label = _label(STATUS_TEXT["offline"], "state")
        self.hint_label = _label("", "muted")
        self.engine_label = _label("", "muted")
        texts.addWidget(self.state_label)
        texts.addWidget(self.hint_label)
        texts.addWidget(self.engine_label)
        state_row.addLayout(texts, 1)
        self.voice_button = _button("Voice")
        self.voice_button.setCheckable(True)
        self.voice_button.setMinimumWidth(110)
        self.voice_button.clicked.connect(self._toggle_voice)
        state_row.addWidget(self.voice_button, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(state_panel)

        self.banner = QFrame()
        self.banner.setProperty("role", "banner")
        banner_row = QHBoxLayout(self.banner)
        banner_row.setContentsMargins(14, 10, 14, 10)
        self.banner_label = _label()
        banner_row.addWidget(self.banner_label, 1)
        self.settings_button = _button("Open speech settings")
        self.settings_button.clicked.connect(self._open_speech_settings)
        banner_row.addWidget(self.settings_button)
        self.retry_button = _button("Try again", "primary")
        self.retry_button.clicked.connect(lambda: self._set_voice(True))
        banner_row.addWidget(self.retry_button)
        self.banner.hide()
        layout.addWidget(self.banner)

        command_row = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText('Type a command, e.g. "open brave"')
        self.command_input.returnPressed.connect(self._send_command)
        self.send_button = _button("Run", "primary")
        self.send_button.clicked.connect(self._send_command)
        command_row.addWidget(self.command_input, 1)
        command_row.addWidget(self.send_button)
        layout.addLayout(command_row)

        self.activity = QTreeWidget()
        self.activity.setHeaderLabels(["Time", "You said", "Result", "Via"])
        self.activity.setRootIsDecorated(False)
        self.activity.setAlternatingRowColors(True)
        self.activity.setUniformRowHeights(True)
        header = self.activity.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.activity, 1)

    # -- connection / status ------------------------------------------------

    def reset(self) -> None:
        self.activity.clear()
        self._seen_ids.clear()
        self._open_row = None
        self._pending_via = ""

    def set_offline(self) -> None:
        self.orb.set_status("offline")
        self.state_label.setText(STATUS_TEXT["offline"])
        self.hint_label.setText("The ATLAS core isn't running.")
        self.voice_button.setEnabled(False)
        self.send_button.setEnabled(False)

    def refresh(self) -> None:
        self.voice_button.setEnabled(True)
        self.send_button.setEnabled(True)
        self._bridge.call(lambda c: c.status(), self.apply_status, self._error)
        self._bridge.call(lambda c: c.history(), self._apply_history, self._error)

    def apply_status(self, status: dict[str, Any]) -> None:
        voice = status["voice"]
        self.wake_phrase = status.get("wake_phrase", "atlas")
        engines = " → ".join(status.get("speech_providers", []))
        self.engine_label.setText(f"Speech: {engines}" if engines else "")
        self.voice_button.setChecked(voice["enabled"])
        self.voice_button.setText("Voice on" if voice["enabled"] else "Voice off")
        if voice["enabled"]:
            if self.orb.status in ("off", "offline"):
                self._show_status("sleeping")
            self.banner.hide()
        else:
            self._show_status("off")
            self._show_voice_error(voice.get("error", ""))

    def _show_status(self, status: str) -> None:
        self.orb.set_status(status)
        self.state_label.setText(STATUS_TEXT.get(status, status))
        if status == "sleeping":
            self.hint_label.setText(f'Say "{self.wake_phrase.title()}", pause, then your command.')
        elif status == "off":
            self.hint_label.setText("Typed commands still work.")
        else:
            self.hint_label.setText("")

    def _show_voice_error(self, error: str) -> None:
        if not error:
            self.banner.hide()
            return
        self.banner_label.setText(error)
        is_speech_setting = "online speech" in error.lower()
        self.settings_button.setVisible(is_speech_setting and sys.platform == "win32")
        self.banner.show()

    # -- actions ------------------------------------------------------------

    def _toggle_voice(self) -> None:
        self._set_voice(self.voice_button.isChecked())

    def _set_voice(self, enabled: bool) -> None:
        self.voice_button.setEnabled(False)

        def done(voice: dict[str, Any]) -> None:
            self.voice_button.setEnabled(True)
            self._bridge.call(lambda c: c.status(), self.apply_status, self._error)

        self._bridge.call(lambda c: c.set_voice(enabled), done, self._error)

    def _send_command(self) -> None:
        text = self.command_input.text().strip()
        if not text:
            return
        self.command_input.clear()
        # The result shows up through the event stream, like voice commands.
        self._bridge.call(lambda c: c.run_command(text), None, self._error)

    def _open_speech_settings(self) -> None:
        open_path(_SPEECH_SETTINGS_URI)

    def _error(self, exc: Exception) -> None:
        self.voice_button.setEnabled(True)
        self._notify(str(exc))

    # -- events -------------------------------------------------------------

    def _apply_history(self, events: list[dict[str, Any]]) -> None:
        for event in events:
            self.on_event(event, live=False)

    def on_event(self, event: dict[str, Any], live: bool = True) -> None:
        event_id = event.get("id")
        if isinstance(event_id, int):
            if event_id in self._seen_ids:
                return
            self._seen_ids.add(event_id)
        kind, message = event["kind"], event.get("message", "")
        when = time.strftime("%H:%M:%S", time.localtime(event.get("time", time.time())))
        if kind == "status" and live:
            self._show_status(message)
        elif kind == "engine":
            self._pending_via = message
        elif kind == "heard":
            via = self._pending_via or ("typed" if event.get("source") == "api" else "voice")
            self._pending_via = ""
            self._open_row = self._add_row(when, message, "…", via)
        elif kind in ("result", "failed"):
            row = self._open_row or self._add_row(when, "", "", event.get("source", ""))
            self._open_row = None
            row.setText(2, message)
            row.setForeground(2, QColor(COLORS["ok"] if kind == "result" else COLORS["fail"]))
        elif kind == "timeout":
            row = self._add_row(when, "(nothing after wake word)", message, "voice")
            row.setForeground(2, QColor(COLORS["muted"]))
        elif kind in ("voice", "reloaded") and live:
            self._bridge.call(lambda c: c.status(), self.apply_status, self._error)

    def _add_row(self, when: str, said: str, result: str, via: str) -> QTreeWidgetItem:
        row = QTreeWidgetItem([when, said, result, via])
        row.setForeground(0, QColor(COLORS["muted"]))
        row.setForeground(3, QColor(COLORS["muted"]))
        self.activity.insertTopLevelItem(0, row)
        while self.activity.topLevelItemCount() > 500:
            self.activity.takeTopLevelItem(self.activity.topLevelItemCount() - 1)
        return row


class ApplicationsPage(QWidget):
    def __init__(self, bridge: CoreBridge, notify: Notify) -> None:
        super().__init__()
        self._bridge = bridge
        self._notify = notify

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addLayout(
            _page_header(
                "Applications",
                'What "open …", "close …" and "switch to …" can reach. Aliases are the '
                "names you say, comma-separated.",
            )
        )
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter")
        self.filter_input.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_input)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Aliases", "Executable"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)  # keep the .exe name visible
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        add = _button("Add")
        add.clicked.connect(self._add_row)
        remove = _button("Remove selected", "danger")
        remove.clicked.connect(self._remove_selected)
        self.discover_button = _button("Discover installed apps")
        self.discover_button.clicked.connect(self._discover)
        self.save_button = _button("Save", "primary")
        self.save_button.clicked.connect(self.save)
        for widget in (add, remove, self.discover_button):
            buttons.addWidget(widget)
        buttons.addStretch(1)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

    def refresh(self) -> None:
        self._bridge.call(lambda c: c.config(), self._load, self._notify_error)

    def _load(self, config: dict[str, Any]) -> None:
        self.table.setRowCount(0)
        for name, entry in sorted(config.get("applications", {}).items()):
            self._append(name, ", ".join(entry.get("aliases", [])), entry.get("executable", ""))
        self._apply_filter(self.filter_input.text())

    def _append(self, name: str, aliases: str, executable: str) -> int:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, value in enumerate((name, aliases, executable)):
            self.table.setItem(row, column, QTableWidgetItem(value))
        return row

    def _add_row(self) -> None:
        self.filter_input.clear()
        row = self._append("", "", "")
        self.table.scrollToBottom()
        item = self.table.item(row, 0)
        if item is not None:
            self.table.editItem(item)

    def _remove_selected(self) -> None:
        for row in sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(row)

    def _apply_filter(self, text: str) -> None:
        needle = text.lower().strip()
        for row in range(self.table.rowCount()):
            values = " ".join(
                (self.table.item(row, c) or QTableWidgetItem()).text() for c in range(3)
            )
            self.table.setRowHidden(row, bool(needle) and needle not in values.lower())

    def collect(self) -> dict[str, dict[str, Any]]:
        """Table -> config["applications"]. Raises ValueError on bad rows."""
        applications: dict[str, dict[str, Any]] = {}
        for row in range(self.table.rowCount()):
            cells = [
                (self.table.item(row, c) or QTableWidgetItem()).text().strip() for c in range(3)
            ]
            name, aliases, executable = cells
            if not any(cells):
                continue
            if not name:
                raise ValueError(f"Row {row + 1} needs a name")
            key = name.lower()
            if key in applications:
                raise ValueError(f'"{name}" is listed twice')
            alias_list = [a.strip().lower() for a in aliases.split(",") if a.strip()]
            applications[key] = {"executable": executable, "aliases": alias_list or [key]}
        return applications

    def save(self) -> None:
        try:
            applications = self.collect()
        except ValueError as exc:
            QMessageBox.warning(self, "Can't save applications", str(exc))
            return

        def write(client: Any) -> dict[str, Any]:
            config = client.config()
            config["applications"] = applications
            return client.update_config(config)

        self.save_button.setEnabled(False)
        self._bridge.call(write, self._saved, self._notify_error)

    def _saved(self, config: dict[str, Any]) -> None:
        self.save_button.setEnabled(True)
        self._load(config)
        self._notify(f"Saved {len(config.get('applications', {}))} applications")

    def _discover(self) -> None:
        self.discover_button.setEnabled(False)
        self._notify("Scanning installed applications…")

        def done(result: dict[str, list[str]]) -> None:
            self.discover_button.setEnabled(True)
            self._notify(
                f"Discovery: {len(result['added'])} added, {len(result['updated'])} updated"
            )
            self.refresh()

        self._bridge.call(lambda c: c.discover_apps(), done, self._notify_error)

    def _notify_error(self, exc: Exception) -> None:
        self.save_button.setEnabled(True)
        self.discover_button.setEnabled(True)
        self._notify(str(exc))


class PluginsPage(QWidget):
    def __init__(self, bridge: CoreBridge, notify: Notify) -> None:
        super().__init__()
        self._bridge = bridge
        self._notify = notify
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addLayout(
            _page_header(
                "Plugins",
                "A plugin that fails to load is disabled on its own; the reason is shown here.",
            )
        )
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Plugin", "Status", "Reason"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

    def refresh(self) -> None:
        self._bridge.call(lambda c: c.plugins(), self._load, lambda e: self._notify(str(e)))

    def _load(self, plugins: list[dict[str, str]]) -> None:
        self.table.setRowCount(0)
        for plugin in plugins:
            row = self.table.rowCount()
            self.table.insertRow(row)
            status = QTableWidgetItem(plugin["status"])
            status.setForeground(
                QColor(COLORS["ok"] if plugin["status"] == "loaded" else COLORS["muted"])
            )
            self.table.setItem(row, 0, QTableWidgetItem(plugin["name"]))
            self.table.setItem(row, 1, status)
            self.table.setItem(row, 2, QTableWidgetItem(plugin["reason"]))


class SettingsPage(QWidget):
    def __init__(self, bridge: CoreBridge, notify: Notify) -> None:
        super().__init__()
        self._bridge = bridge
        self._notify = notify

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addLayout(_page_header("Settings", "Saved to config.toml; applied immediately."))

        panel = _panel()
        form = QFormLayout(panel)
        form.setContentsMargins(18, 16, 18, 16)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(18)

        self.engine = QComboBox()
        self.engine.addItem("Windows speech (same as Win+H)", "windows")
        self.engine.addItem("Vosk (offline, needs a model)", "vosk")
        self.engine.currentIndexChanged.connect(self._update_engine_fields)
        self.wake_phrase = QLineEdit()
        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(2.0, 30.0)
        self.timeout.setSingleStep(0.5)
        self.timeout.setSuffix(" s")
        self.model_path = QLineEdit()
        self.model_path.setPlaceholderText("auto-detect under models/")
        self.providers = QLineEdit()
        self.providers.setPlaceholderText("native, cloud")
        self.device = QLineEdit()
        self.confirm = QCheckBox("Ask before shutdown, restart and other dangerous commands")
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])

        form.addRow("Speech engine", self.engine)
        form.addRow("Wake word", self.wake_phrase)
        form.addRow("Listen for", self.timeout)
        form.addRow("Recognizers after wake", self.providers)
        form.addRow("Microphone", self.device)
        self._vosk_rows = [(_label("Vosk model"), self.model_path)]
        for label, field in self._vosk_rows:
            form.addRow(label, field)
        form.addRow("Safety", self.confirm)
        form.addRow("Log level", self.log_level)
        layout.addWidget(panel)

        self.engine_note = _label("", "muted")
        layout.addWidget(self.engine_note)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.save_button = _button("Save", "primary")
        self.save_button.clicked.connect(self.save)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)
        layout.addStretch(1)

    def refresh(self) -> None:
        self._bridge.call(lambda c: c.config(), self.load, self._error)

    def load(self, config: dict[str, Any]) -> None:
        speech, wake = config["speech"], config["wake"]
        index = self.engine.findData(speech["engine"])
        self.engine.setCurrentIndex(max(index, 0))
        self.wake_phrase.setText(wake["phrase"])
        self.timeout.setValue(float(wake["timeout_seconds"]))
        self.model_path.setText(speech.get("model_path", ""))
        self.providers.setText(", ".join(speech.get("providers", [])))
        self.device.setText(config["audio"]["device"])
        self.confirm.setChecked(bool(config["commands"]["require_confirmation"]))
        self.log_level.setCurrentText(config["logging"]["level"].upper())
        self._update_engine_fields()

    def _update_engine_fields(self) -> None:
        vosk = self.engine.currentData() == "vosk"
        for label, field in self._vosk_rows:
            label.setVisible(vosk)
            field.setVisible(vosk)
        self.engine_note.setText(
            "Windows speech: the wake word and the command are both recognized on this PC. "
            "Recognizers for the command are tried in order: native (Windows offline), "
            "cloud (needs ATLAS_STT_API_KEY)."
            if not vosk
            else "Vosk: wake word and final fallback run offline. Recognizers for the command "
            "are tried in order: native (Windows offline), cloud (needs ATLAS_STT_API_KEY)."
        )

    def apply_to(self, config: dict[str, Any]) -> dict[str, Any]:
        phrase = self.wake_phrase.text().strip().lower()
        if not phrase:
            raise ValueError("The wake word can't be empty")
        config["speech"]["engine"] = self.engine.currentData()
        config["speech"]["model_path"] = self.model_path.text().strip()
        config["speech"]["providers"] = [
            p.strip() for p in self.providers.text().split(",") if p.strip()
        ]
        config["wake"]["phrase"] = phrase
        config["wake"]["timeout_seconds"] = self.timeout.value()
        config["audio"]["device"] = self.device.text().strip() or "default"
        config["commands"]["require_confirmation"] = self.confirm.isChecked()
        config["logging"]["level"] = self.log_level.currentText()
        return config

    def save(self) -> None:
        try:
            self.apply_to({"speech": {}, "wake": {}, "audio": {}, "commands": {}, "logging": {}})
        except ValueError as exc:
            QMessageBox.warning(self, "Can't save settings", str(exc))
            return

        def write(client: Any) -> dict[str, Any]:
            return client.update_config(self.apply_to(client.config()))

        self.save_button.setEnabled(False)
        self._bridge.call(write, self._saved, self._error)

    def _saved(self, config: dict[str, Any]) -> None:
        self.save_button.setEnabled(True)
        self.load(config)
        self._notify("Settings saved")

    def _error(self, exc: Exception) -> None:
        self.save_button.setEnabled(True)
        self._notify(str(exc))


class LogsPage(QWidget):
    def __init__(self, bridge: CoreBridge, notify: Notify) -> None:
        super().__init__()
        self._bridge = bridge
        self._notify = notify
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addLayout(_page_header("Logs", "The last 500 lines of the core's log."))
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Cascadia Mono")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(9)
        self.text.setFont(font)
        layout.addWidget(self.text, 1)
        buttons = QHBoxLayout()
        refresh = _button("Refresh")
        refresh.clicked.connect(self.refresh)
        buttons.addWidget(refresh)
        folder = _button("Open log folder")
        folder.clicked.connect(self._open_folder)
        buttons.addWidget(folder)
        buttons.addStretch(1)
        layout.addLayout(buttons)

    def refresh(self) -> None:
        self._bridge.call(lambda c: c.logs(500), self._load, lambda e: self._notify(str(e)))

    def _load(self, lines: list[str]) -> None:
        self.text.setPlainText("\n".join(lines))
        bar = self.text.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _open_folder(self) -> None:
        from atlas.utils.paths import get_log_dir

        open_path(str(get_log_dir()))
