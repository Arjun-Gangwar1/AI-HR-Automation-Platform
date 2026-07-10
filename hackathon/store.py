"""
store.py — SQLite persistence + recruitment pipeline state machine.

Why this exists
───────────────
The app previously kept everything in in-memory dicts (`current_session`,
`active_jobs`), so a server restart wiped all jobs, candidates, and pipeline
progress. This module persists that state to a small SQLite database so the
demo survives restarts, and adds a formal pipeline state machine (see the
notebook page 3: JD → approved → posted → collecting → ... → onboarding).

Design
──────
- Stdlib `sqlite3` only (no new dependency, no ORM).
- A new connection per operation (`check_same_thread` safe for FastAPI's
  thread pool); fine for a single-recruiter demo workload.
- Flexible JSON blobs for the session and each job, plus a dedicated
  `stage_history` audit table.

This layer is ADDITIVE: `main.py` keeps its in-memory working copies for the
request lifecycle and simply calls `save_session()` / `advance_stage()` after
mutations, and restores state on startup.
"""
import os
import json
import sqlite3
from datetime import datetime
from typing import Optional

_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
_DB_PATH = os.path.join(_DB_DIR, "hr_state.db")


# ══════════════════════════════════════════════════════════════
# PIPELINE STATE MACHINE
# ══════════════════════════════════════════════════════════════

# Ordered stages of the hiring pipeline. The pipeline only ever moves
# FORWARD to the furthest stage reached (advance_stage never regresses),
# so out-of-order endpoint calls can't rewind visible progress.
STAGES = [
    "IDLE",          # nothing started
    "JD_DRAFTED",    # a JD has been generated
    "POSTED",        # JD approved & posted to Telegram
    "COLLECTING",    # resumes are being uploaded
    "SCREENED",      # resumes scored by the screening agent
    "SHORTLISTED",   # HR picked a shortlist
    "INTERVIEWING",  # interview emails drafted/sent, slots booked
    "OFFER",         # offer letter generated / sent
    "ONBOARDING",    # welcome package sent, onboarding started
]

STAGE_LABELS = {
    "IDLE": "Not started",
    "JD_DRAFTED": "JD drafted",
    "POSTED": "JD posted",
    "COLLECTING": "Collecting applications",
    "SCREENED": "Resumes screened",
    "SHORTLISTED": "Candidates shortlisted",
    "INTERVIEWING": "Interviewing",
    "OFFER": "Offer stage",
    "ONBOARDING": "Onboarding",
}


def _stage_index(stage: str) -> int:
    try:
        return STAGES.index(stage)
    except ValueError:
        return 0


# ══════════════════════════════════════════════════════════════
# CONNECTION + SCHEMA
# ══════════════════════════════════════════════════════════════

def _connect() -> sqlite3.Connection:
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                job_id    TEXT PRIMARY KEY,
                data      TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS stage_history (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                stage TEXT NOT NULL,
                at    TEXT NOT NULL
            );
            """
        )
        # Ensure a starting stage exists.
        cur = conn.execute("SELECT value FROM app_state WHERE key = 'stage'")
        if cur.fetchone() is None:
            conn.execute(
                "INSERT INTO app_state (key, value) VALUES ('stage', ?)", ("IDLE",)
            )


# ══════════════════════════════════════════════════════════════
# SESSION (the current recruitment pipeline working state)
# ══════════════════════════════════════════════════════════════

def save_session(session: dict) -> None:
    """Persist the entire in-memory session dict as one JSON blob."""
    try:
        payload = json.dumps(session, default=str)
    except (TypeError, ValueError):
        return  # never let persistence crash a request
    with _connect() as conn:
        conn.execute(
            "INSERT INTO app_state (key, value) VALUES ('session', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (payload,),
        )


def load_session() -> Optional[dict]:
    """Return the persisted session dict, or None if none saved yet."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM app_state WHERE key = 'session'"
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["value"])
    except (TypeError, ValueError):
        return None


# ══════════════════════════════════════════════════════════════
# STAGE MACHINE
# ══════════════════════════════════════════════════════════════

def get_stage() -> str:
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM app_state WHERE key = 'stage'"
        ).fetchone()
    return row["value"] if row else "IDLE"


def advance_stage(target: str) -> str:
    """
    Move the pipeline to `target` only if it's further along than the
    current stage (never regresses). Records an audit entry on change.
    Returns the resulting stage.
    """
    if target not in STAGES:
        return get_stage()
    current = get_stage()
    if _stage_index(target) <= _stage_index(current):
        return current
    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO app_state (key, value) VALUES ('stage', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (target,),
        )
        conn.execute(
            "INSERT INTO stage_history (stage, at) VALUES (?, ?)", (target, now)
        )
    return target


def reset_stage() -> None:
    """Reset the pipeline back to IDLE (e.g. when starting a fresh role)."""
    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO app_state (key, value) VALUES ('stage', 'IDLE') "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        )
        conn.execute(
            "INSERT INTO stage_history (stage, at) VALUES ('IDLE', ?)", (now,)
        )


def get_stage_history(limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT stage, at FROM stage_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"stage": r["stage"], "label": STAGE_LABELS.get(r["stage"], r["stage"]),
             "at": r["at"]} for r in rows]


# ══════════════════════════════════════════════════════════════
# JOBS (posting-agent job records, so history survives restart)
# ══════════════════════════════════════════════════════════════

def save_job(job: dict) -> None:
    job_id = job.get("job_id")
    if not job_id:
        return
    try:
        payload = json.dumps(job, default=str)
    except (TypeError, ValueError):
        return
    with _connect() as conn:
        conn.execute(
            "INSERT INTO jobs (job_id, data, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(job_id) DO UPDATE SET data = excluded.data, "
            "updated_at = excluded.updated_at",
            (job_id, payload, datetime.now().isoformat()),
        )


def load_jobs() -> dict:
    """Return all persisted jobs keyed by job_id (matches active_jobs shape)."""
    with _connect() as conn:
        rows = conn.execute("SELECT job_id, data FROM jobs").fetchall()
    jobs = {}
    for r in rows:
        try:
            jobs[r["job_id"]] = json.loads(r["data"])
        except (TypeError, ValueError):
            continue
    return jobs
