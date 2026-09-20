from atlas.__main__ import build_parser, main


def test_version_flag(capsys):
    exit_code = main(["--version"])
    assert exit_code == 0
    assert "ATLAS" in capsys.readouterr().out


def test_diagnose_flag_runs_without_crashing(capsys):
    exit_code = main(["--diagnose"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Python" in out


def test_list_monitors_does_not_crash(capsys):
    exit_code = main(["--list-monitors"])
    assert exit_code == 0


def test_parser_accepts_all_documented_flags():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--test-microphone",
            "--test-speech",
            "--list-devices",
            "--list-monitors",
            "--list-windows",
            "--list-plugins",
            "--reload",
            "--tray",
        ]
    )
    assert args.test_microphone
    assert args.tray
