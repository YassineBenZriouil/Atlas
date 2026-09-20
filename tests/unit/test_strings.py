from atlas.utils.strings import normalize


def test_normalize_monitor_two():
    assert normalize("Monitor two") == "monitor 2"


def test_normalize_vs_code():
    assert normalize("V S code") == "vs code"


def test_normalize_collapses_whitespace():
    assert normalize("  open   brave  ") == "open brave"


def test_normalize_does_not_convert_unrelated_to():
    assert normalize("go to brave") == "go to brave"


def test_normalize_lowercases():
    assert normalize("OPEN BRAVE") == "open brave"
