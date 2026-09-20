from atlas.commands.entities import extract_dimensions, extract_monitor_number, extract_volume_level


def test_extract_monitor_number():
    assert extract_monitor_number("move brave to monitor 2") == 2


def test_extract_monitor_number_missing():
    assert extract_monitor_number("move brave") is None


def test_extract_volume_level_clamped():
    assert extract_volume_level("set volume to 150") == 100


def test_extract_volume_level_negative_clamped():
    assert extract_volume_level("volume -10") is None


def test_extract_dimensions():
    assert extract_dimensions("resize brave to 800 by 600") == (800, 600)
