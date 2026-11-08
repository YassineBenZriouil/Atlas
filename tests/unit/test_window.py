"""The window against a fake core client, rendered offscreen."""

from __future__ import annotations

import copy
import os
import queue
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from atlas.config.schema import AtlasConfig  # noqa: E402
from atlas.service.client import CoreInfo  # noqa: E402
from atlas.ui.window import MainWindow  # noqa: E402

ONLINE_OFF = "Windows online speech recognition is off - turn it on in Settings"


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    yield QApplication.instance() or QApplication([])


def wait_for(condition, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


class FakeClient:
    def __init__(self, pid: int = 42) -> None:
        from dataclasses import asdict

        self.info = CoreInfo(port=1, token="t", pid=pid)
        self._config = asdict(AtlasConfig())
        self._config["applications"] = {"brave": {"executable": "", "aliases": ["brave"]}}
        self.voice = {"enabled": False, "error": ONLINE_OFF}
        self.commands: list[str] = []
        self.voice_calls: list[bool] = []
        self.saved: list[dict] = []
        self.queue: queue.Queue = queue.Queue()
        self.history_events = [
            {"id": 1, "time": 0, "kind": "heard", "message": "open brave", "source": "api"},
            {"id": 2, "time": 0, "kind": "result", "message": "Opened brave", "source": "api"},
        ]
        self.quit_called = False

    def status(self):
        return {
            "version": "x",
            "pid": self.info.pid,
            "voice": dict(self.voice),
            "speech_providers": ["windows"],
            "wake_phrase": self._config["wake"]["phrase"],
        }

    def history(self):
        return list(self.history_events)

    def config(self):
        return copy.deepcopy(self._config)

    def update_config(self, config):
        self.saved.append(copy.deepcopy(config))
        self._config = copy.deepcopy(config)
        return self.config()

    def plugins(self):
        return [{"name": "spotify", "status": "disabled", "reason": "no credentials"}]

    def logs(self, lines=200):
        return ["line one", "line two"]

    def run_command(self, text):
        self.commands.append(text)
        return {"success": True, "message": "ok"}

    def set_voice(self, enabled):
        self.voice_calls.append(enabled)
        self.voice = {"enabled": enabled, "error": ""}
        return dict(self.voice)

    def discover_apps(self):
        return {"added": ["notepad"], "updated": []}

    def quit(self):
        self.quit_called = True

    def events(self):
        while True:
            event = self.queue.get()
            if event is None:
                return
            yield event


@pytest.fixture
def window():
    client = FakeClient()
    win = MainWindow(client_provider=lambda: client, autostart=False)
    assert wait_for(lambda: win.bridge.client is client)
    yield win, client
    win.close()
    client.queue.put(None)


def activity_rows(win):
    tree = win.live.activity
    return [
        [tree.topLevelItem(i).text(c) for c in range(4)] for i in range(tree.topLevelItemCount())
    ]


def test_history_and_status_load_on_connect(window):
    win, _ = window
    assert wait_for(lambda: len(activity_rows(win)) == 1)
    assert activity_rows(win)[0][1:] == ["open brave", "Opened brave", "typed"]
    assert win.live.engine_label.text() == "Speech: windows"
    assert not win.live.voice_button.isChecked()


def test_online_speech_error_shows_banner_with_settings_button(window):
    win, _ = window
    assert wait_for(lambda: win.live.banner.isVisibleTo(win))
    assert "online speech" in win.live.banner_label.text().lower()
    assert win.live.settings_button.isVisibleTo(win) == (os.name == "nt")


def test_live_voice_events_render_with_provider(window):
    win, client = window
    for event in (
        {"id": 10, "time": 0, "kind": "status", "message": "listening", "source": "voice"},
        {"id": 11, "time": 0, "kind": "engine", "message": "windows", "source": "voice"},
        {"id": 12, "time": 0, "kind": "heard", "message": "mute", "source": "voice"},
        {"id": 13, "time": 0, "kind": "failed", "message": "No audio device", "source": "voice"},
        {"id": 13, "time": 0, "kind": "failed", "message": "duplicate", "source": "voice"},
    ):
        client.queue.put(event)
    assert wait_for(lambda: activity_rows(win) and activity_rows(win)[0][2] == "No audio device")
    assert activity_rows(win)[0][1:] == ["mute", "No audio device", "windows"]
    assert win.live.orb.status == "listening"
    assert sum(r[2] == "duplicate" for r in activity_rows(win)) == 0


def test_typed_command_and_voice_toggle_reach_core(window):
    win, client = window
    win.live.command_input.setText("  open brave ")
    win.live.send_button.click()
    assert wait_for(lambda: client.commands == ["open brave"])
    win.live.voice_button.click()
    assert wait_for(lambda: client.voice_calls == [True])
    assert wait_for(lambda: win.live.voice_button.text() == "Voice on")
    assert wait_for(lambda: not win.live.banner.isVisibleTo(win))


def test_settings_page_saves_only_its_fields(window):
    win, client = window
    win.nav.setCurrentRow(3)
    assert wait_for(lambda: win.settings.wake_phrase.text() == "atlas")
    win.settings.wake_phrase.setText("Computer")
    win.settings.engine.setCurrentIndex(win.settings.engine.findData("vosk"))
    win.settings.save_button.click()
    assert wait_for(lambda: len(client.saved) == 1)
    saved = client.saved[0]
    assert saved["wake"]["phrase"] == "computer"
    assert saved["speech"]["engine"] == "vosk"
    assert saved["applications"] == client.config()["applications"]  # untouched


def test_settings_rejects_empty_wake_word(window, monkeypatch):
    win, client = window
    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    win.nav.setCurrentRow(3)
    assert wait_for(lambda: win.settings.wake_phrase.text() == "atlas")
    win.settings.wake_phrase.setText("  ")
    win.settings.save_button.click()
    assert warnings and not client.saved


def test_applications_edit_and_save(window, monkeypatch):
    win, client = window
    win.nav.setCurrentRow(1)
    page = win.applications
    assert wait_for(lambda: page.table.rowCount() == 1)
    page.table.item(0, 1).setText("brave, browser")
    row = page._append("Notes", "", "C:/notes.exe")
    assert row == 1
    page.save_button.click()
    assert wait_for(lambda: len(client.saved) == 1)
    assert client.saved[0]["applications"] == {
        "brave": {"executable": "", "aliases": ["brave", "browser"]},
        "notes": {"executable": "C:/notes.exe", "aliases": ["notes"]},
    }

    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    page._append("brave", "", "")
    page.save_button.click()
    assert warnings and "twice" in warnings[0]
    assert len(client.saved) == 1


def test_plugins_and_logs_pages(window):
    win, _ = window
    win.nav.setCurrentRow(2)
    assert wait_for(lambda: win.plugins.table.rowCount() == 1)
    assert win.plugins.table.item(0, 2).text() == "no credentials"
    win.nav.setCurrentRow(4)
    assert wait_for(lambda: win.logs.text.toPlainText() == "line one\nline two")


def test_quit_asks_then_stops_core(window, monkeypatch):
    win, client = window
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.No)
    win.quit_button.click()
    QApplication.processEvents()
    assert not client.quit_called
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.Yes)
    win.quit_button.click()
    assert wait_for(lambda: client.quit_called)


def test_offline_core_disables_controls_and_offers_start():
    win = MainWindow(client_provider=lambda: None, autostart=False)
    assert wait_for(lambda: win.live.state_label.text() == "Not connected")
    assert not win.live.send_button.isEnabled()
    assert not win.quit_button.isEnabled()
    assert win.start_button.isVisibleTo(win)
    win.close()


def test_reconnect_to_new_core_resets_activity():
    clients = [FakeClient(pid=1), FakeClient(pid=2)]
    current = {"client": clients[0]}
    win = MainWindow(client_provider=lambda: current["client"], autostart=False)
    win.bridge._retry_seconds = 0.05
    assert wait_for(lambda: len(activity_rows(win)) == 1)
    clients[1].history_events = []
    current["client"] = clients[1]
    clients[0].queue.put(None)  # first core's stream ends
    assert wait_for(lambda: win.bridge.client is clients[1])
    assert wait_for(lambda: activity_rows(win) == [])
    win.close()
    clients[1].queue.put(None)
