from datetime import datetime

from whiscode.reminders import next_milestone


def test_before_first_milestone():
    now = datetime(2026, 3, 22, 9, 0, 0)
    hour, wake = next_milestone(now, set())
    assert hour == 12
    assert wake == datetime(2026, 3, 22, 12, 0, 0)


def test_between_milestones():
    now = datetime(2026, 3, 22, 14, 30, 0)
    hour, wake = next_milestone(now, {12})
    assert hour == 17
    assert wake == datetime(2026, 3, 22, 17, 0, 0)


def test_after_last_milestone():
    now = datetime(2026, 3, 22, 23, 30, 0)
    hour, wake = next_milestone(now, {12, 17, 23})
    assert hour == 12
    assert wake == datetime(2026, 3, 23, 12, 0, 0)


def test_skips_shown_milestones():
    now = datetime(2026, 3, 22, 11, 0, 0)
    hour, wake = next_milestone(now, {12})
    assert hour == 17
    assert wake == datetime(2026, 3, 22, 17, 0, 0)


def test_all_future_shown_wraps_to_tomorrow():
    now = datetime(2026, 3, 22, 16, 0, 0)
    hour, wake = next_milestone(now, {17, 23})
    assert hour == 12
    assert wake == datetime(2026, 3, 23, 12, 0, 0)
