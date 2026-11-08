"""The core service over real HTTP on 127.0.0.1, with fake Windows-layer
managers injected so commands never touch the desktop."""

from __future__ import annotations

import threading
import time

import pytest
import requests
from tests.fixtures.fakes import (
    FakeApplicationManager,
    FakeKeyboardController,
    FakeMonitorManager,
    FakeMouseController,
    FakeSystemController,
    FakeWindowManager,
)

from atlas.application.app import Application
from atlas.application.voice_loop import VoiceUnavailableError
from atlas.config.loader import ConfigError, config_from_dict
from atlas.service.client import (
    CoreApiError,
    CoreClient,
    CoreInfo,
    connect,
    read_discovery,
    remove_discovery,
    write_discovery,
)
from atlas.service.core import AtlasCore
from atlas.service.server import CoreServer, run_core


def make_app() -> Application:
    window_manager = FakeWindowManager()
    return Application(
        window_manager=window_manager,
        monitor_manager=FakeMonitorManager(),
        keyboard_controller=FakeKeyboardController(),
        mouse_controller=FakeMouseController(),
        system_controller=FakeSystemController(),
        application_manager=FakeApplicationManager(window_manager),
    )


def no_voice(app, on_event=None):
    raise VoiceUnavailableError("No Vosk model found")


@pytest.fixture
def served():
    core = AtlasCore(app_factory=make_app, voice_factory=no_voice)
    core.start()
    server = CoreServer(core)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = CoreClient(CoreInfo(port=server.port, token=server.token, pid=0))
    server.thread = thread  # type: ignore[attr-defined]
    yield core, server, client
    server.shutdown()
    core.shutdown()
    server.server_close()


def test_requests_without_token_are_rejected(served):
    _, server, _ = served
    url = f"http://127.0.0.1:{server.port}/api/status"
    assert requests.get(url, timeout=5).status_code == 401
    bad = {"Authorization": "Bearer wrong"}
    assert (
        requests.post(url.replace("status", "command"), headers=bad, timeout=5).status_code == 401
    )


def test_command_runs_and_lands_in_history(served):
    _, _, client = served
    result = client.run_command("atlas status")
    assert result["success"]
    kinds = [(e["kind"], e["message"]) for e in client.history()]
    assert ("heard", "atlas status") in kinds
    assert any(kind == "result" for kind, _ in kinds)
    assert client.run_command("do a backflip")["success"] is False
    assert client.history()[-1]["kind"] == "failed"


def test_bad_requests_get_400_and_unknown_routes_404(served):
    _, _, client = served
    with pytest.raises(CoreApiError) as exc:
        client.request("POST", "/api/command", {"text": "   "})
    assert exc.value.status == 400
    with pytest.raises(CoreApiError) as exc:
        client.request("POST", "/api/voice", {"enabled": "yes"})
    assert exc.value.status == 400
    with pytest.raises(CoreApiError) as exc:
        client.request("GET", "/api/nope")
    assert exc.value.status == 404


def test_event_stream_delivers_live_events(served):
    core, _, client = served
    received: list[dict] = []

    def listen():
        for event in client.events():
            received.append(event)
            if event["kind"] == "result":
                return

    listener = threading.Thread(target=listen, daemon=True)
    listener.start()
    deadline = time.monotonic() + 5
    while not core.events._subscribers and time.monotonic() < deadline:
        time.sleep(0.01)
    client.run_command("atlas test")
    listener.join(timeout=5)
    assert [e["kind"] for e in received] == ["heard", "result"]
    assert received[0]["source"] == "api"


def test_voice_unavailable_is_reported_not_raised(served):
    _, _, client = served
    assert client.set_voice(True) == {"enabled": False, "error": "No Vosk model found"}
    assert client.status()["voice"]["enabled"] is False


def test_config_update_saves_and_reloads(served):
    _, _, client = served
    config = client.config()
    config["wake"]["phrase"] = "computer"
    assert client.update_config(config)["wake"]["phrase"] == "computer"
    assert client.status()["wake_phrase"] == "computer"
    assert any(e["kind"] == "reloaded" for e in client.history())
    assert client.run_command("atlas status")["success"]  # rebuilt app still works


@pytest.mark.parametrize(
    "patch",
    [
        {"wake": "computer"},
        {"wake": {"timeout_seconds": "soon"}},
        {"speech": {"providers": "native"}},
        {"applications": {"brave": {"bogus": 1}}},
        {"config_version": 999},
    ],
)
def test_invalid_config_is_rejected_without_saving(served, patch):
    _, _, client = served
    before = client.config()
    with pytest.raises(CoreApiError) as exc:
        client.update_config({**before, **patch})
    assert exc.value.status == 400
    assert client.config() == before


def test_config_from_dict_accepts_int_for_float():
    assert config_from_dict({"wake": {"timeout_seconds": 5}}).wake.timeout_seconds == 5
    with pytest.raises(ConfigError):
        config_from_dict({"wake": {"timeout_seconds": True}})


def test_plugins_and_logs(served):
    _, _, client = served
    assert all({"name", "status", "reason"} <= set(p) for p in client.plugins())
    assert isinstance(client.logs(5), list)
    assert len(client.logs(5)) <= 5


def test_quit_stops_server_and_ends_event_stream(served):
    core, server, client = served
    stream_done = threading.Event()

    def drain():
        for _ in client.events():
            pass
        stream_done.set()

    threading.Thread(target=drain, daemon=True).start()
    deadline = time.monotonic() + 5
    while not core.events._subscribers and time.monotonic() < deadline:
        time.sleep(0.01)
    client.quit()
    server.thread.join(timeout=5)
    assert not server.thread.is_alive()
    core.shutdown()  # what run_core does once serve_forever returns
    assert stream_done.wait(timeout=5)


def test_discovery_roundtrip_and_connect(served):
    _, server, _ = served
    assert connect() is None  # no discovery file yet
    info = CoreInfo(port=server.port, token=server.token, pid=123)
    write_discovery(info)
    assert read_discovery() == info
    assert connect() is not None
    assert run_core() == 1  # single instance: a live core already answers

    remove_discovery(CoreInfo(port=1, token="other", pid=1))
    assert read_discovery() == info  # someone else's info never removes ours
    remove_discovery(info)
    assert read_discovery() is None


def test_stale_discovery_is_ignored():
    write_discovery(CoreInfo(port=1, token="x", pid=1))
    assert connect() is None


class FakeVoice:
    def __init__(self, app, on_event=None):
        self.on_event = on_event
        self.stopped = False

    def start(self):
        pass

    def stop(self):
        self.stopped = True


def test_voice_that_dies_at_runtime_is_reported_off():
    voices: list[FakeVoice] = []

    def factory(app, on_event=None):
        voices.append(FakeVoice(app, on_event))
        return voices[-1]

    core = AtlasCore(app_factory=make_app, voice_factory=factory)
    core.start()
    assert core.status()["voice"] == {"enabled": True, "error": ""}
    voices[0].on_event("voice_lost", "mic unplugged")
    assert core.status()["voice"] == {"enabled": False, "error": "mic unplugged"}
    assert core.events.history()[-1]["kind"] == "voice"
    assert core.set_voice(True)  # can be turned back on
    core.shutdown()
    assert voices[1].stopped


def test_unsupported_platform_action_is_http_501(served, monkeypatch):
    import atlas.platform

    _, _, client = served
    monkeypatch.setattr(atlas.platform, "get_backend", atlas.platform._fallback_backend)
    with pytest.raises(CoreApiError) as exc:
        client.discover_apps()
    assert exc.value.status == 501
    assert "isn't supported" in str(exc.value)
