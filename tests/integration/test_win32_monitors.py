"""Real, read-only Win32 calls - safe to run in every test session."""

from atlas.windows.monitors import Win32MonitorManager


def test_list_monitors_returns_at_least_one():
    monitors = Win32MonitorManager().list_monitors()
    assert len(monitors) >= 1
    assert any(m.is_primary for m in monitors)


def test_get_primary_monitor():
    primary = Win32MonitorManager().get_primary_monitor()
    assert primary.is_primary


def test_get_monitor_out_of_range_returns_none():
    assert Win32MonitorManager().get_monitor(999) is None


def test_get_monitor_matches_list():
    manager = Win32MonitorManager()
    monitors = manager.list_monitors()
    assert manager.get_monitor(monitors[0].index) == monitors[0]
