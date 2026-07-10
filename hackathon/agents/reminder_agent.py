"""
Reminder Agent — automatic day-of interview reminders.

`calendar_service.reminder_service.send_reminders_for_today()` already scans
today's Google Calendar events and emails HR + attendees. This module wires it
to run automatically every morning (default 08:00 in the configured timezone)
via APScheduler, and exposes a manual trigger for on-demand sends / testing.
"""
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from calendar_service.reminder_service import send_reminders_for_today

load_dotenv()

TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", 8))  # 8 AM local time

_scheduler: BackgroundScheduler | None = None


def start_reminder_scheduler() -> None:
    """Start the daily reminder job (idempotent — safe to call once on startup)."""
    global _scheduler
    if _scheduler is not None:
        return
    try:
        _scheduler = BackgroundScheduler(timezone=TIMEZONE)
        _scheduler.add_job(
            _run_daily_reminders,
            CronTrigger(hour=REMINDER_HOUR, minute=0, timezone=TIMEZONE),
            id="daily_interview_reminders",
            replace_existing=True,
        )
        _scheduler.start()
        print(f"[Reminders] Daily reminder job scheduled for {REMINDER_HOUR:02d}:00 {TIMEZONE}.")
    except Exception as e:
        print(f"[Reminders] Could not start scheduler: {e}")


def _run_daily_reminders() -> None:
    print(f"[Reminders] Running day-of reminders at {datetime.now().isoformat()}")
    try:
        result = send_reminders_for_today()
        print(result)
    except Exception as e:
        print(f"[Reminders] Error while sending: {e}")


def send_reminders_now() -> dict:
    """Manually trigger reminders for today's events (used by the API endpoint)."""
    try:
        result = send_reminders_for_today()
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
