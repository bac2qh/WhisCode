from pathlib import Path

from whiscode.main import parse_args


def test_parse_args_defaults_to_hotkey_mode():
    args = parse_args([])

    assert args.hands_free is False
    assert args.hotkey == "shift_r"


def test_parse_args_hands_free_options():
    args = parse_args([
        "--hands-free",
        "--hands-free-wake-dir",
        "/tmp/wake",
        "--hands-free-end-dir",
        "/tmp/end",
        "--hands-free-threshold",
        "0.2",
        "--hands-free-window-seconds",
        "1.5",
        "--hands-free-slide-seconds",
        "0.1",
        "--hands-free-tail-seconds",
        "0.75",
        "--hands-free-max-seconds",
        "30",
        "--hands-free-debug",
    ])

    assert args.hands_free is True
    assert args.hands_free_wake_dir == Path("/tmp/wake")
    assert args.hands_free_end_dir == Path("/tmp/end")
    assert args.hands_free_threshold == 0.2
    assert args.hands_free_window_seconds == 1.5
    assert args.hands_free_slide_seconds == 0.1
    assert args.hands_free_tail_seconds == 0.75
    assert args.hands_free_max_seconds == 30
    assert args.hands_free_debug is True
