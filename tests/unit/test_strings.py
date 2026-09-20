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


def test_normalize_volume_with_filler_word():
    assert normalize("set volume to thirty") == "set volume to 30"


def test_normalize_move_to_monitor_unaffected_by_filler_fix():
    assert normalize("move brave to monitor two") == "move brave to monitor 2"
