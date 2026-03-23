import threading
from datetime import datetime, timedelta

from whiscode.stats import Stats

MILESTONES = {
    12: "Lunch time! Take a break.",
    17: "End of workday! Time to wrap up.",
    23: "Getting late! Time for bed.",
}


def next_milestone(now: datetime, shown_today: set[int]) -> tuple[int, datetime]:
    """Return the next (hour, wake_time) milestone that hasn't been shown today."""
    for hour in sorted(MILESTONES):
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target > now and hour not in shown_today:
            return hour, target

    # All today's milestones passed; aim for first milestone tomorrow
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    first_hour = min(MILESTONES)
    target = tomorrow.replace(hour=first_hour)
    return first_hour, target


def _reminder_loop(stats: Stats):
    shown_today: set[int] = set()
    current_date = datetime.now().date()

    while True:
        now = datetime.now()
        if now.date() != current_date:
            shown_today.clear()
            current_date = now.date()

        hour, wake_time = next_milestone(now, shown_today)
        sleep_seconds = (wake_time - now).total_seconds()
        if sleep_seconds > 0:
            threading.Event().wait(timeout=sleep_seconds)

        now = datetime.now()
        if now >= wake_time and hour not in shown_today:
            shown_today.add(hour)
            msg = MILESTONES[hour]
            print(f"\n--- {msg} Session stats: {stats.summary()} ---\n")


def start_reminders(stats: Stats):
    t = threading.Thread(target=_reminder_loop, args=(stats,), daemon=True)
    t.start()
