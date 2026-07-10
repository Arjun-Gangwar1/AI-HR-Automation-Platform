"""
test_phase2.py — one-command smoke test for the HR AI Platform (Phases 0-2).

WHAT IT CHECKS (no external API keys required)
----------------------------------------------
1. IMPORT: the whole app + every agent imports cleanly — proves all
   dependencies (openai, apscheduler, reportlab, google libs, ...) are installed
   and there are no syntax/wiring errors.
2. ENDPOINTS: boots the real FastAPI app via TestClient (against a throwaway
   SQLite DB) and hits every endpoint that does NOT call OpenAI / Gmail /
   Google Calendar, asserting correct responses — pipeline state machine,
   persistence, offers, onboarding checklist, CSV export, and error handling.

WHAT IT DOES NOT CHECK
----------------------
Endpoints that call external services (JD generation, screening, email send,
inbox IMAP, calendar booking, negotiation LLM) need real credentials in .env.
Those are listed at the end as "needs live creds".

RUN:  python test_phase2.py       (from the hackathon/ directory)
Exit code 0 = all smoke checks passed.
"""
import os
import sys
import tempfile
import traceback

# Run from this file's directory so relative paths (static/, data/) resolve.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PASS, FAIL = 0, 0
FAILURES = []


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  [OK] {name}")
        PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}\n       {e}")
        FAIL += 1
        FAILURES.append((name, traceback.format_exc()))


# -- 1. IMPORT LAYER -------------------------------------------
print("\n[1/2] Import check (validates all dependencies + wiring)")

_import_errors = []
try:
    import store  # noqa
    # Point persistence at a throwaway DB so we never touch real state.
    _tmp = tempfile.mkdtemp()
    store._DB_DIR = _tmp
    store._DB_PATH = os.path.join(_tmp, "smoke.db")
    import main  # noqa  — imports FastAPI app + all 11 agents
    store.init_db()
    print("  [OK] import main + store + all agents")
    PASS += 1
except Exception as e:
    print(f"  [FAIL] import failed: {e}")
    traceback.print_exc()
    FAIL += 1
    _import_errors.append(e)

if _import_errors:
    print("\nAborting: the app could not be imported (likely a missing dependency).")
    print("Fix:  pip install -r requirements.txt")
    sys.exit(1)

from fastapi.testclient import TestClient

# Plain TestClient (no `with`) so we skip the heavy startup lifespan
# (BERT knowledge-base load / scheduler). We initialised the DB manually above.
client = TestClient(main.app)


# -- 2. ENDPOINT LAYER -----------------------------------------
print("\n[2/2] Endpoint checks (no external creds needed)")


def t_pipeline():
    r = client.get("/api/pipeline")
    assert r.status_code == 200, r.status_code
    body = r.json()
    assert body["current_stage"] in [s["key"] for s in body["stages"]]
    assert len(body["stages"]) == 9, body["stages"]


def t_reset():
    r = client.post("/api/pipeline/reset")
    assert r.status_code == 200 and r.json()["current_stage"] == "IDLE"


def t_session():
    r = client.get("/api/session")
    assert r.status_code == 200 and "current_stage" in r.json()


def t_jd_styles():
    r = client.get("/api/jd-styles")
    assert r.status_code == 200 and isinstance(r.json()["styles"], dict)


def t_analytics():
    r = client.get("/api/analytics")
    assert r.status_code == 200 and "funnel" in r.json()


def t_offers_empty():
    r = client.get("/api/offers")
    assert r.status_code == 200 and r.json()["offers"] == {}


def t_onboarding_checklist():
    r = client.get("/api/onboarding/checklist", params={"candidate_id": "nobody"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 8 and body["received_count"] == 0


def t_csv_export():
    r = client.get("/api/export/candidates.csv")
    assert r.status_code == 200
    assert "candidate_id" in r.text and "offer_status" in r.text


def t_job_status():
    r = client.get("/api/job-status")
    assert r.status_code == 200 and "session" in r.json()


# --- error-path checks (validate guards, no external calls) ---
def t_screen_no_resumes():
    r = client.post("/api/screen-resumes")
    assert r.status_code == 400, f"expected 400, got {r.status_code}"


def t_inbox_no_candidates():
    r = client.post("/api/inbox/check", json={"days_back": 3})
    assert r.status_code == 400, f"expected 400, got {r.status_code}"


def t_offer_response_unknown():
    r = client.post("/api/offer/response", json={"candidate_id": "ghost", "response": "accepted"})
    assert r.status_code == 404, f"expected 404, got {r.status_code}"


def t_negotiate_unknown():
    r = client.post("/api/offer/negotiate", json={"candidate_id": "ghost"})
    assert r.status_code == 404, f"expected 404, got {r.status_code}"


def t_stage_advances_and_persists():
    # Directly drive the state machine + persistence (no LLM needed).
    store.advance_stage("SHORTLISTED")
    assert store.get_stage() == "SHORTLISTED"
    # forward-only guard
    store.advance_stage("JD_DRAFTED")
    assert store.get_stage() == "SHORTLISTED"
    r = client.get("/api/pipeline")
    assert r.json()["current_stage"] == "SHORTLISTED"


for name, fn in [
    ("GET  /api/pipeline (9-stage machine)", t_pipeline),
    ("POST /api/pipeline/reset", t_reset),
    ("GET  /api/session (has current_stage)", t_session),
    ("GET  /api/jd-styles", t_jd_styles),
    ("GET  /api/analytics", t_analytics),
    ("GET  /api/offers (empty)", t_offers_empty),
    ("GET  /api/onboarding/checklist (8 items)", t_onboarding_checklist),
    ("GET  /api/export/candidates.csv", t_csv_export),
    ("GET  /api/job-status", t_job_status),
    ("POST /api/screen-resumes -> 400 (no resumes)", t_screen_no_resumes),
    ("POST /api/inbox/check -> 400 (no candidates)", t_inbox_no_candidates),
    ("POST /api/offer/response -> 404 (unknown)", t_offer_response_unknown),
    ("POST /api/offer/negotiate -> 404 (unknown)", t_negotiate_unknown),
    ("state machine advances + persists (forward-only)", t_stage_advances_and_persists),
]:
    check(name, fn)


# -- SUMMARY ---------------------------------------------------
print("\n" + "=" * 60)
print(f"  SMOKE TEST: {PASS} passed, {FAIL} failed")
print("=" * 60)

print("""
Not covered here (need real creds in .env — test manually once configured):
  - POST /api/generate-jd          (OpenAI)
  - POST /api/screen-resumes       (OpenAI, with resumes)
  - POST /api/post-jd              (Telegram)
  - POST /api/send-emails          (Gmail SMTP)
  - POST /api/inbox/check          (Gmail IMAP, with candidates)
  - POST /api/offer/negotiate      (OpenAI, with a real candidate)
  - POST /api/calendar/* , /schedule-intro  (Google Calendar OAuth)
""")

sys.exit(1 if FAIL else 0)
