"""
Posting Agent - Post JDs to Telegram via DM (direct message) and auto-relax if low responses
"""
import os
import re
import requests
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from agents.jd_agent import relax_jd

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
APPLICATION_THRESHOLD = int(os.getenv("APPLICATION_THRESHOLD", 5))
RELAXATION_INTERVAL_HOURS = int(os.getenv("RELAXATION_INTERVAL_HOURS", 48))

# In-memory job store
active_jobs: dict = {}
scheduler = BackgroundScheduler()
scheduler.start()


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram HTML mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_telegram_message(text: str, chat_id: str = "", parse_mode: str = "HTML") -> Optional[int]:
    """Send a DM to the specified chat_id via Telegram Bot API. Returns message_id."""
    target_chat = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not target_chat:
        print("[Telegram] WARNING: Bot token or chat ID not configured.")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        data = response.json()
        if data.get("ok"):
            print(f"[Telegram] Message sent successfully to {target_chat}")
            return data["result"]["message_id"]
        else:
            error_desc = data.get('description', 'Unknown error')
            print(f"[Telegram] API Error: {error_desc}")
            # Retry without formatting if HTML fails
            if 'parse' in error_desc.lower():
                payload["parse_mode"] = ""
                fallback = requests.post(url, json=payload, timeout=15)
                fb_data = fallback.json()
                if fb_data.get("ok"):
                    print("[Telegram] Sent without formatting (fallback)")
                    return fb_data["result"]["message_id"]
            return None
    except Exception as e:
        print(f"[Telegram] Send failed: {e}")
        return None


def test_telegram_connection(chat_id: str = "") -> dict:
    """Send a test message to verify the bot + chat_id works."""
    target = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN:
        return {"ok": False, "error": "No TELEGRAM_BOT_TOKEN set in .env"}
    if not target:
        return {"ok": False, "error": "No chat ID provided"}
    
    msg_id = send_telegram_message(
        "✅ <b>Bot connected successfully!</b>\n\nYour HR AI Agent is linked to this chat.",
        target
    )
    if msg_id:
        return {"ok": True, "message_id": msg_id, "chat_id": target}
    else:
        return {"ok": False, "error": "Failed to send. Make sure you've started a chat with the bot first, and the chat ID is correct."}


def format_jd_for_telegram(jd: str, role: str, version: int = 1) -> str:
    """Format JD in HTML for Telegram."""
    # First escape the raw JD text
    safe_jd = _escape_html(jd)
    
    # Convert markdown bold **text** to <b>text</b>
    safe_jd = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe_jd)
    # Convert markdown bold *text* to <b>text</b>  
    safe_jd = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'<b>\1</b>', safe_jd)
    # Convert - bullet points to • 
    safe_jd = re.sub(r'^\s*[-•]\s*', '• ', safe_jd, flags=re.MULTILINE)
    
    safe_role = _escape_html(role)
    header = f"🚀 <b>NEW JOB OPENING</b> (v{version})\n{'─'*30}\n\n"
    footer = f"\n\n{'─'*30}\n📩 Reply to this message to apply!\n🏷 #{safe_role.replace(' ', '_')} #hiring"
    
    full_text = header + safe_jd + footer
    
    # Truncate if too long (Telegram limit: 4096 chars)
    if len(full_text) > 4000:
        full_text = full_text[:3950] + "...\n\n" + footer
    return full_text


def post_jd(job_id: str, jd: str, role: str, chat_id: str = "") -> dict:
    """Post JD to Telegram DM and register relaxation scheduler."""
    version = 1
    target_chat = chat_id or TELEGRAM_CHAT_ID
    
    message_text = format_jd_for_telegram(jd, role, version)
    msg_id = send_telegram_message(message_text, target_chat)
    
    active_jobs[job_id] = {
        "job_id": job_id,
        "role": role,
        "current_jd": jd,
        "original_jd": jd,
        "version": version,
        "telegram_message_id": msg_id,
        "telegram_chat_id": target_chat,
        "posted_at": datetime.now().isoformat(),
        "application_count": 0,
        "relaxation_history": [],
        "status": "active"
    }
    
    # Schedule auto-relaxation check
    run_time = datetime.now() + timedelta(hours=RELAXATION_INTERVAL_HOURS)
    scheduler.add_job(
        check_and_relax,
        'date',
        run_date=run_time,
        args=[job_id],
        id=f"relax_{job_id}",
        replace_existing=True
    )
    print(f"[Posting] JD for '{role}' sent via Telegram DM. Next check at {run_time.isoformat()}")
    
    return active_jobs[job_id]


def check_and_relax(job_id: str):
    """Auto-called by scheduler: if low applications, relax JD and repost."""
    if job_id not in active_jobs:
        return
    
    job = active_jobs[job_id]
    app_count = job["application_count"]
    
    print(f"[Relaxation] Job '{job['role']}' has {app_count} applications (threshold: {APPLICATION_THRESHOLD})")
    
    if app_count < APPLICATION_THRESHOLD:
        print(f"[Relaxation] Below threshold — relaxing JD for '{job['role']}'...")
        try:
            relaxed_jd = relax_jd(
                job["current_jd"],
                reason=f"only {app_count} applications in {RELAXATION_INTERVAL_HOURS} hours"
            )
            
            new_version = job["version"] + 1
            message_text = format_jd_for_telegram(relaxed_jd, job["role"], new_version)
            msg_id = send_telegram_message(message_text, job.get("telegram_chat_id", ""))
            
            active_jobs[job_id]["relaxation_history"].append({
                "version": job["version"],
                "relaxed_at": datetime.now().isoformat(),
                "app_count_at_relaxation": app_count,
                "old_jd": job["current_jd"]
            })
            active_jobs[job_id]["current_jd"] = relaxed_jd
            active_jobs[job_id]["version"] = new_version
            active_jobs[job_id]["telegram_message_id"] = msg_id
            
            print(f"[Relaxation] Relaxed JD v{new_version} posted for '{job['role']}'")
            
            # Schedule next check
            run_time = datetime.now() + timedelta(hours=RELAXATION_INTERVAL_HOURS)
            scheduler.add_job(
                check_and_relax,
                'date',
                run_date=run_time,
                args=[job_id],
                id=f"relax_{job_id}",
                replace_existing=True
            )
        except Exception as e:
            print(f"[Relaxation] Error: {e}")
    else:
        print(f"[Relaxation] Sufficient applications — no relaxation needed.")


def reschedule_pending_relaxations():
    """
    After a restart, re-arm the auto-relaxation check for every active job.
    APScheduler's in-memory jobs don't survive a restart, so jobs restored from
    SQLite would otherwise never be re-checked. We schedule the next check at
    posted_at + interval, or shortly from now if that time has already passed.
    """
    now = datetime.now()
    rescheduled = 0
    for job_id, job in active_jobs.items():
        if job.get("status") != "active":
            continue
        try:
            posted_at = datetime.fromisoformat(job.get("posted_at", now.isoformat()))
        except (ValueError, TypeError):
            posted_at = now
        run_time = posted_at + timedelta(hours=RELAXATION_INTERVAL_HOURS)
        if run_time <= now:
            run_time = now + timedelta(minutes=5)  # overdue → check soon
        scheduler.add_job(
            check_and_relax, 'date', run_date=run_time,
            args=[job_id], id=f"relax_{job_id}", replace_existing=True,
        )
        rescheduled += 1
    if rescheduled:
        print(f"[Posting] Re-armed relaxation checks for {rescheduled} restored job(s).")
    return rescheduled


def increment_application_count(job_id: str):
    if job_id in active_jobs:
        active_jobs[job_id]["application_count"] += 1


def get_job_status(job_id: str) -> Optional[dict]:
    return active_jobs.get(job_id)


def get_all_jobs() -> list:
    return list(active_jobs.values())
