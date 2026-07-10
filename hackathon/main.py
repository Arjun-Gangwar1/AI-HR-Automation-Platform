"""
Main FastAPI Server — HR AI Agent Unified Backend
"""
import os
import uuid
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

# Import agents
from agents.jd_agent import generate_jd, get_styles
from agents.posting_agent import post_jd, get_job_status, get_all_jobs, active_jobs, test_telegram_connection
from agents.screening_agent import screen_resumes
from agents.email_agent import draft_interview_email, send_email, draft_rejection_email
from agents.calendar_agent import schedule_interview, get_all_events, get_events_for_month, add_event, delete_event
from agents.helpdesk_agent import answer_query, load_knowledge_base
from agents.onboarding_agent import send_welcome_package
from agents.interview_agent import generate_interview_questions
from agents.document_agent import generate_offer_letter, generate_company_handbook
from agents.inbox_agent import check_replies
from agents.negotiation_agent import negotiation_guidance
from agents.reminder_agent import start_reminder_scheduler, send_reminders_now
from agents.onboarding_agent import get_document_checklist, schedule_intro_meeting
from utils.pdf_utils import extract_text_from_pdf
import io
import csv
from fastapi.responses import StreamingResponse
import store

app = FastAPI(title="HR AI Agent", version="2.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# === In-memory state ===
current_session: dict = {
    "current_jd": None,
    "current_role": None,
    "current_job_id": None,
    "resumes": [],
    "screened": [],
    "shortlisted": [],
    "draft_emails": {},
    "calendar_events": {},
    # Phase 2 additions (persisted automatically via the JSON session blob)
    "offers": {},          # candidate_id -> {status, salary, sent_at, response, reason}
    "onboarding": {},      # candidate_id -> {documents_collected: [...], intro_meeting: {...}}
    "inbox_replies": [],   # latest classified candidate replies
}


def _find_candidate(candidate_id: str = "", email: str = "") -> dict | None:
    """Locate a candidate by id or email across shortlisted then screened lists."""
    pools = current_session.get("shortlisted", []) + current_session.get("screened", [])
    for c in pools:
        if candidate_id and c.get("candidate_id") == candidate_id:
            return c
        if email and (c.get("email") or "").lower() == email.lower():
            return c
    return None


def persist(stage: str = "") -> None:
    """Save the current session to SQLite and optionally advance the pipeline
    stage. Called after mutating endpoints so state survives a restart."""
    try:
        store.save_session(current_session)
        if stage:
            store.advance_stage(stage)
    except Exception as e:  # persistence must never break a request
        print(f"[Store] persist warning: {e}")

# === Pydantic Models ===
class GenerateJDRequest(BaseModel):
    title: str
    department: Optional[str] = ""
    experience_level: Optional[str] = ""
    preferred_skills: Optional[str] = ""
    required_vs_nice: Optional[str] = ""
    excluded_skills: Optional[str] = ""
    candidate_types: List[str] = []
    work_modes: List[str] = []
    notice_periods: List[str] = []
    project_preferences: Optional[str] = ""
    domain_preferences: Optional[str] = ""
    style: Optional[str] = "Standard Corporate"

class PostJDRequest(BaseModel):
    jd: str
    role: str
    chat_id: Optional[str] = ""

class TestTelegramRequest(BaseModel):
    chat_id: str

class ShortlistRequest(BaseModel):
    candidate_ids: List[str]

class InterviewRequest(BaseModel):
    candidate_id: str

class DraftEmailsRequest(BaseModel):
    interview_time: str
    interview_link: Optional[str] = ""

class SendEmailsRequest(BaseModel):
    confirmed: bool

class HelpdeskRequest(BaseModel):
    question: str

class OnboardRequest(BaseModel):
    candidate_email: str
    role: str
    salary: str = "$120,000"

class AddEventRequest(BaseModel):
    title: str
    datetime_str: str
    event_type: Optional[str] = "interview"
    candidate_name: Optional[str] = ""
    candidate_email: Optional[str] = ""
    notes: Optional[str] = ""
    duration_minutes: Optional[int] = 60

class OfferLetterRequest(BaseModel):
    candidate_name: str
    role: str
    salary: str
    equity: str
    start_date: str

class HandbookRequest(BaseModel):
    company_name: str
    core_values: str
    perks: str


# --- Phase 2 models ---

class InboxCheckRequest(BaseModel):
    days_back: Optional[int] = 7
    mark_seen: Optional[bool] = False

class OfferSendRequest(BaseModel):
    candidate_id: Optional[str] = ""
    candidate_email: Optional[str] = ""
    role: Optional[str] = ""
    salary: str = "$120,000"
    equity: Optional[str] = "Standard equity package"
    start_date: Optional[str] = ""

class OfferResponseRequest(BaseModel):
    candidate_id: str
    response: str  # "accepted" or "declined"
    reason: Optional[str] = ""

class NegotiateRequest(BaseModel):
    candidate_id: str
    reason: Optional[str] = ""

class DocumentReceivedRequest(BaseModel):
    candidate_id: str
    document: str
    received: bool = True

class ScheduleIntroRequest(BaseModel):
    candidate_id: str
    datetime_str: Optional[str] = ""
    duration_minutes: Optional[int] = 30


# === Routes ===

@app.get("/")
async def serve_dashboard():
    return FileResponse("static/index.html")


# --- JD Generator ---

@app.get("/api/jd-styles")
async def api_jd_styles():
    """Return available JD styles."""
    return {"styles": get_styles()}


@app.post("/api/generate-jd")
async def api_generate_jd(req: GenerateJDRequest):
    """Generate JD from structured preferences."""
    try:
        jd = generate_jd(req.dict())
        current_session["current_jd"] = jd
        current_session["current_role"] = req.title
        persist(stage="JD_DRAFTED")
        return {"jd": jd, "role": req.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Telegram Posting ---

@app.post("/api/test-telegram")
async def api_test_telegram(req: TestTelegramRequest):
    """Send a test message to verify Telegram bot + chat ID."""
    result = test_telegram_connection(req.chat_id)
    if result["ok"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@app.post("/api/post-jd")
async def api_post_jd(req: PostJDRequest):
    """Approve & post JD to Telegram DM."""
    try:
        job_id = str(uuid.uuid4())[:8]
        current_session["current_job_id"] = job_id
        current_session["current_jd"] = req.jd
        current_session["current_role"] = req.role
        result = post_jd(job_id, req.jd, req.role, req.chat_id or "")
        if job_id in active_jobs:
            store.save_job(active_jobs[job_id])
        persist(stage="POSTED")
        return {
            "job_id": job_id,
            "message": "JD sent via Telegram DM successfully!",
            "telegram_message_id": result.get("telegram_message_id"),
            "next_relaxation_check": f"In {os.getenv('RELAXATION_INTERVAL_HOURS', 48)} hours"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Resume Upload & Screening ---

@app.post("/api/upload-resumes")
async def api_upload_resumes(files: List[UploadFile] = File(...)):
    """Upload multiple PDF/TXT resumes."""
    current_session["resumes"] = []
    current_session["screened"] = []
    
    uploaded = []
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in (".pdf", ".txt"):
            continue
        content = await file.read()
        
        if ext == ".pdf":
            text = extract_text_from_pdf(content)
        else:
            text = content.decode("utf-8", errors="ignore")
        
        os.makedirs("data/resumes", exist_ok=True)
        save_path = f"data/resumes/{file.filename}"
        with open(save_path, "wb") as f:
            f.write(content)
        
        current_session["resumes"].append({
            "filename": file.filename,
            "text": text
        })
        uploaded.append(file.filename)
        
        job_id = current_session.get("current_job_id")
        if job_id and job_id in active_jobs:
            active_jobs[job_id]["application_count"] += 1
            store.save_job(active_jobs[job_id])

    persist(stage="COLLECTING" if uploaded else "")
    return {
        "uploaded_count": len(uploaded),
        "filenames": uploaded,
        "message": f"{len(uploaded)} resumes uploaded successfully"
    }


@app.post("/api/screen-resumes")
async def api_screen_resumes():
    """Run BERT screening on uploaded resumes."""
    if not current_session["resumes"]:
        raise HTTPException(status_code=400, detail="No resumes uploaded yet")
    jd = current_session.get("current_jd")
    if not jd:
        raise HTTPException(status_code=400, detail="No active JD. Generate one first.")
    
    try:
        results = screen_resumes(current_session["resumes"], jd)
        current_session["screened"] = results
        persist(stage="SCREENED")
        return {
            "total": len(results),
            "candidates": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Shortlisting ---

@app.post("/api/shortlist")
async def api_shortlist(req: ShortlistRequest):
    shortlisted = [
        c for c in current_session["screened"]
        if c.get("candidate_id") in req.candidate_ids
    ]
    current_session["shortlisted"] = shortlisted
    persist(stage="SHORTLISTED" if shortlisted else "")
    return {
        "shortlisted_count": len(shortlisted),
        "candidates": shortlisted
    }

@app.post("/api/interview-questions")
async def api_interview_questions(req: InterviewRequest):
    candidate = next(
        (c for c in current_session.get("shortlisted", []) if c.get("candidate_id") == req.candidate_id),
        None
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    jd = current_session.get("current_jd", "")
    questions = generate_interview_questions(
        jd=jd,
        candidate_summary=candidate.get("summary", ""),
        candidate_skills=candidate.get("skills", []),
        candidate_projects=candidate.get("projects", [])
    )
    return {"questions": questions}

# --- Email Center ---

@app.post("/api/draft-emails")
async def api_draft_emails(req: DraftEmailsRequest):
    if not current_session["shortlisted"]:
        raise HTTPException(status_code=400, detail="No shortlisted candidates")
    
    role = current_session.get("current_role", "the role")
    drafts = {}
    
    for candidate in current_session["shortlisted"]:
        body = draft_interview_email(
            candidate, role, req.interview_time, req.interview_link
        )
        subject = f"Interview Invitation — {role} Position | {candidate.get('name')}"
        cid = candidate.get("candidate_id")
        drafts[cid] = {
            "name": candidate["name"],
            "email": candidate["email"],
            "subject": subject,
            "body": body
        }
    
    current_session["draft_emails"] = drafts
    persist(stage="INTERVIEWING")
    return {"drafts": drafts}


@app.post("/api/send-emails")
async def api_send_emails(req: SendEmailsRequest, interview_datetime: str = "", meeting_link: str = ""):
    if not req.confirmed:
        raise HTTPException(status_code=400, detail="Not confirmed by HR")
    if not current_session["draft_emails"]:
        raise HTTPException(status_code=400, detail="No draft emails. Run draft-emails first.")
    
    role = current_session.get("current_role", "the role")
    results = {}
    
    for cid, draft in current_session["draft_emails"].items():
        candidate = next(
            (c for c in current_session["shortlisted"] if c.get("candidate_id") == cid),
            {"name": "Candidate", "email": draft["email"]}
        )
        email = candidate.get("email")
        if not email:
            email = "no-reply@example.com"
        
        email_result = {"sent": False, "error": None}
        try:
            send_email(email, draft["subject"], draft["body"])
            email_result["sent"] = True
        except Exception as e:
            email_result["error"] = str(e)
        
        cal_result = {"status": "skipped"}
        if interview_datetime:
            try:
                cal_result = schedule_interview(
                    candidate, interview_datetime, role,
                    meeting_link=meeting_link
                )
            except Exception as e:
                cal_result = {"status": "error", "message": str(e)}
        
        current_session["calendar_events"][email] = cal_result
        results[email] = {
            "name": draft["name"],
            "email_sent": email_result["sent"],
            "calendar": cal_result
        }

    persist(stage="INTERVIEWING")
    return {"results": results}

@app.post("/api/send-rejections")
async def api_send_rejections():
    """Send constructive rejection emails to all non-shortlisted candidates."""
    if not current_session.get("screened"):
        raise HTTPException(status_code=400, detail="No candidates screened yet")
        
    role = current_session.get("current_role", "the role")
    jd = current_session.get("current_jd", "")
    shortlisted_ids = {c.get("candidate_id") for c in current_session.get("shortlisted", [])}
    
    rejected = [c for c in current_session["screened"] if c.get("candidate_id") not in shortlisted_ids]
    if not rejected:
        return {"message": "No candidates to reject. Everyone was shortlisted!"}
        
    results = {}
    for candidate in rejected:
        email = candidate.get("email")
        if not email:
            continue
            
        body = draft_rejection_email(candidate, role, jd)
        subject = f"Update regarding your application for {role} at Our Company"
        
        try:
            send_email(email, subject, body)
            results[email] = "sent"
        except Exception as e:
            results[email] = f"failed: {str(e)}"
            
    return {"message": f"Processed {len(results)} rejection emails", "details": results}

# --- Calendar ---

@app.get("/api/calendar/events")
async def api_calendar_events(year: int = 0, month: int = 0):
    """Get all calendar events, optionally filtered by month."""
    if year and month:
        events = get_events_for_month(year, month)
    else:
        events = get_all_events()
    return {"events": events}


@app.post("/api/calendar/events")
async def api_add_calendar_event(req: AddEventRequest):
    """Add a new calendar event."""
    event = add_event(
        title=req.title,
        datetime_str=req.datetime_str,
        event_type=req.event_type,
        candidate_name=req.candidate_name,
        candidate_email=req.candidate_email,
        notes=req.notes,
        duration_minutes=req.duration_minutes,
    )
    return event


@app.delete("/api/calendar/events/{event_id}")
async def api_delete_calendar_event(event_id: str):
    """Delete a calendar event."""
    if delete_event(event_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Event not found")

@app.post("/api/calendar/auto-schedule")
async def api_auto_schedule_interviews():
    """
    Autonomous Meeting Scheduler Agent:
    Takes all shortlisted candidates and sequentially auto-books them.
    """
    try:
        shortlisted = current_session.get("shortlisted", [])
        if not shortlisted:
            raise HTTPException(status_code=400, detail="No shortlisted candidates found.")
            
        role = current_session.get("current_role", "Interview")
        
        from agents.calendar_agent import auto_schedule_interviews
        result = auto_schedule_interviews(
            candidates=shortlisted,
            role=role,
            duration_minutes=45,
            max_per_day=4
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])

        persist(stage="INTERVIEWING")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Helpdesk ---

@app.post("/api/helpdesk")
async def api_helpdesk(req: HelpdeskRequest):
    try:
        answer = answer_query(req.question)
        return {"question": req.question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Onboarding ---

@app.post("/api/onboard")
async def api_onboard(req: OnboardRequest):
    candidate = next(
        (c for c in current_session["shortlisted"] if c["email"] == req.candidate_email),
        {"name": "New Employee", "email": req.candidate_email}
    )
    # Inject salary into the dictionary so agent can use it
    candidate["salary"] = req.salary
    try:
        result = send_welcome_package(candidate, req.role)
        persist(stage="ONBOARDING")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Document Generator ---

@app.post("/api/documents/offer-letter")
async def api_generate_offer_letter(req: OfferLetterRequest):
    try:
        html_content = generate_offer_letter(
            candidate_name=req.candidate_name,
            role=req.role,
            salary=req.salary,
            equity=req.equity,
            start_date=req.start_date
        )
        persist(stage="OFFER")
        return {"html": html_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/handbook")
async def api_generate_handbook(req: HandbookRequest):
    try:
        html_content = generate_company_handbook(
            company_name=req.company_name,
            core_values=req.core_values,
            perks=req.perks
        )
        return {"html": html_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Phase 2: Inbound tracking ---

@app.post("/api/inbox/check")
async def api_inbox_check(req: InboxCheckRequest):
    """Scan the HR inbox for candidate replies, classify them, and update state.
    Confirmed/declined replies auto-update any matching offer status."""
    candidates = current_session.get("shortlisted", []) or current_session.get("screened", [])
    if not candidates:
        raise HTTPException(status_code=400, detail="No candidates to track replies for.")

    result = check_replies(candidates, days_back=req.days_back or 7, mark_seen=req.mark_seen or False)
    replies = result.get("replies", [])
    current_session["inbox_replies"] = replies

    # Auto-update offer status when a reply clearly accepts/declines.
    offers = current_session.setdefault("offers", {})
    for r in replies:
        cid = r.get("candidate_id")
        if cid and cid in offers:
            if r.get("intent") == "confirmed":
                offers[cid]["response"] = "accepted"
            elif r.get("intent") == "declined":
                offers[cid]["response"] = "declined"

    persist()
    return result


# --- Phase 2: Auto reminders ---

@app.post("/api/reminders/send-today")
async def api_send_reminders():
    """Manually trigger day-of interview reminders (HR + attendees).
    Also runs automatically each morning via the reminder scheduler."""
    return send_reminders_now()


# --- Phase 2: Offer tracking + negotiation branch ---

@app.post("/api/offer/send")
async def api_offer_send(req: OfferSendRequest):
    """Generate the offer letter, email it to the candidate, and record the offer."""
    candidate = _find_candidate(req.candidate_id, req.candidate_email)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found. Screen/shortlist first.")

    cid = candidate.get("candidate_id", req.candidate_id)
    role = req.role or current_session.get("current_role", "the role")
    name = candidate.get("name", "Candidate")
    to_email = candidate.get("email", "") or req.candidate_email

    html = generate_offer_letter(
        candidate_name=name, role=role, salary=req.salary,
        equity=req.equity or "", start_date=req.start_date or "",
    )

    body = (
        f"Dear {name},\n\n"
        f"We are delighted to offer you the position of {role}.\n\n"
        f"Base salary: {req.salary}\n"
        f"Equity/Bonus: {req.equity}\n"
        f"Proposed start date: {req.start_date or 'to be confirmed'}\n\n"
        f"Your formal offer letter is being prepared. Please reply to this email to "
        f"accept, or let us know if you'd like to discuss any of the terms.\n\n"
        f"Warm regards,\nHR Team"
    )
    subject = f"Your Offer — {role} Position"

    email_sent = False
    email_error = None
    if to_email:
        try:
            send_email(to_email, subject, body)
            email_sent = True
        except Exception as e:
            email_error = str(e)

    current_session.setdefault("offers", {})[cid] = {
        "name": name,
        "email": to_email,
        "role": role,
        "salary": req.salary,
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
        "response": None,
        "reason": "",
    }
    persist(stage="OFFER")
    return {
        "candidate_id": cid,
        "html": html,
        "email_sent": email_sent,
        "email_error": email_error,
        "offer": current_session["offers"][cid],
    }


@app.get("/api/offers")
async def api_offers():
    """Return all tracked offers and their responses."""
    return {"offers": current_session.get("offers", {})}


@app.post("/api/offer/response")
async def api_offer_response(req: OfferResponseRequest):
    """Record a candidate's response to their offer (accepted / declined)."""
    offers = current_session.get("offers", {})
    if req.candidate_id not in offers:
        raise HTTPException(status_code=404, detail="No offer on record for this candidate.")

    resp = req.response.strip().lower()
    if resp not in ("accepted", "declined"):
        raise HTTPException(status_code=400, detail="response must be 'accepted' or 'declined'")

    offers[req.candidate_id]["response"] = resp
    offers[req.candidate_id]["reason"] = req.reason or ""
    persist()

    next_step = (
        "Proceed to onboarding — start the document checklist and schedule the intro meeting."
        if resp == "accepted"
        else "Consider negotiation: call /api/offer/negotiate for guidance, or send a rejection."
    )
    return {"candidate_id": req.candidate_id, "response": resp, "next_step": next_step}


@app.post("/api/offer/negotiate")
async def api_offer_negotiate(req: NegotiateRequest):
    """Get negotiation guidance for HR after a candidate declines / pushes back."""
    candidate = _find_candidate(req.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    offer = current_session.get("offers", {}).get(req.candidate_id, {})
    role = offer.get("role") or current_session.get("current_role", "the role")
    salary = offer.get("salary", "unspecified")
    guidance = negotiation_guidance(candidate, role, salary, req.reason or "")
    return {"candidate_id": req.candidate_id, "guidance": guidance}


# --- Phase 2: Onboarding document collection + intro meeting ---

@app.get("/api/onboarding/checklist")
async def api_onboarding_checklist(candidate_id: str):
    """Return the new-hire document checklist + collection status for a candidate."""
    ob = current_session.get("onboarding", {}).get(candidate_id, {})
    collected = ob.get("documents_collected", [])
    candidate = _find_candidate(candidate_id)
    checklist = get_document_checklist(collected)
    checklist["candidate_id"] = candidate_id
    checklist["candidate_name"] = candidate.get("name", "") if candidate else ""
    checklist["intro_meeting"] = ob.get("intro_meeting")
    return checklist


@app.post("/api/onboarding/document-received")
async def api_onboarding_document_received(req: DocumentReceivedRequest):
    """Mark an onboarding document as received (or unreceived) for a candidate."""
    ob = current_session.setdefault("onboarding", {}).setdefault(req.candidate_id, {})
    collected = ob.setdefault("documents_collected", [])
    if req.received and req.document not in collected:
        collected.append(req.document)
    elif not req.received and req.document in collected:
        collected.remove(req.document)
    persist(stage="ONBOARDING")
    return get_document_checklist(collected)


@app.post("/api/onboarding/schedule-intro")
async def api_onboarding_schedule_intro(req: ScheduleIntroRequest):
    """Schedule the new-hire intro / orientation meeting on Google Calendar."""
    candidate = _find_candidate(req.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    role = current_session.get("current_role", "the role")
    try:
        result = schedule_intro_meeting(
            candidate, role,
            datetime_str=req.datetime_str or "",
            duration_minutes=req.duration_minutes or 30,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    ob = current_session.setdefault("onboarding", {}).setdefault(req.candidate_id, {})
    ob["intro_meeting"] = result
    persist(stage="ONBOARDING")
    return result


# --- Phase 2: Spreadsheet / CSV export ---

@app.get("/api/export/candidates.csv")
async def api_export_candidates_csv():
    """Export the current candidate pipeline (screened + statuses) as CSV."""
    shortlisted_ids = {c.get("candidate_id") for c in current_session.get("shortlisted", [])}
    offers = current_session.get("offers", {})
    onboarding = current_session.get("onboarding", {})

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "candidate_id", "name", "email", "phone", "score",
        "shortlisted", "offer_status", "offer_response",
        "docs_collected", "intro_meeting_scheduled", "top_skills",
    ])
    for c in current_session.get("screened", []):
        cid = c.get("candidate_id", "")
        offer = offers.get(cid, {})
        ob = onboarding.get(cid, {})
        writer.writerow([
            cid,
            c.get("name", ""),
            c.get("email", ""),
            c.get("phone", ""),
            c.get("final_score", ""),
            "yes" if cid in shortlisted_ids else "no",
            offer.get("status", ""),
            offer.get("response", "") or "",
            len(ob.get("documents_collected", [])),
            "yes" if ob.get("intro_meeting") else "no",
            "; ".join(c.get("skills", [])[:5]),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=candidates.csv"},
    )


# --- Status ---

@app.get("/api/job-status")
async def api_job_status():
    jobs = get_all_jobs()
    session_job_id = current_session.get("current_job_id")
    current_job = get_job_status(session_job_id) if session_job_id else None
    return {
        "all_jobs": jobs,
        "current_job": current_job,
        "session": {
            "role": current_session.get("current_role"),
            "resumes_uploaded": len(current_session.get("resumes", [])),
            "screened": len(current_session.get("screened", [])),
            "shortlisted": len(current_session.get("shortlisted", [])),
        }
    }


@app.get("/api/session")
async def api_session():
    return {
        "current_role": current_session.get("current_role"),
        "current_job_id": current_session.get("current_job_id"),
        "has_jd": current_session.get("current_jd") is not None,
        "resumes_count": len(current_session.get("resumes", [])),
        "screened_count": len(current_session.get("screened", [])),
        "shortlisted_count": len(current_session.get("shortlisted", [])),
        "draft_emails_count": len(current_session.get("draft_emails", {})),
        "current_stage": store.get_stage(),
    }

@app.get("/api/pipeline")
async def api_pipeline():
    """Return the current recruitment pipeline stage + full stage list + history.
    Backed by SQLite so it reflects real, restart-safe progress."""
    current = store.get_stage()
    return {
        "current_stage": current,
        "current_label": store.STAGE_LABELS.get(current, current),
        "stages": [
            {"key": s, "label": store.STAGE_LABELS.get(s, s)}
            for s in store.STAGES
        ],
        "current_index": store.STAGES.index(current) if current in store.STAGES else 0,
        "history": store.get_stage_history(),
        "role": current_session.get("current_role"),
    }


@app.post("/api/pipeline/reset")
async def api_pipeline_reset():
    """Start a fresh role: clear the session and reset the pipeline to IDLE."""
    current_session.update({
        "current_jd": None,
        "current_role": None,
        "current_job_id": None,
        "resumes": [],
        "screened": [],
        "shortlisted": [],
        "draft_emails": {},
        "calendar_events": {},
        "offers": {},
        "onboarding": {},
        "inbox_replies": [],
    })
    store.reset_stage()
    store.save_session(current_session)
    return {"message": "Pipeline reset to IDLE.", "current_stage": "IDLE"}


@app.get("/api/analytics")
async def api_analytics():
    """Return aggregated stats for the dashboard charts."""
    resumes_uploaded = len(current_session.get("resumes", []))
    screened = len(current_session.get("screened", []))
    shortlisted = len(current_session.get("shortlisted", []))
    drafts = len(current_session.get("draft_emails", {}))
    
    return {
        "funnel": {
            "Uploaded": resumes_uploaded,
            "Screened": screened,
            "Shortlisted": shortlisted,
            "Invites Sent": drafts
        },
        "sources": {
            "LinkedIn": 45,
            "Website": 25,
            "Referral": 15,
            "Other": 15
        }
    }


# === Startup ===
@app.on_event("startup")
async def startup_event():
    load_knowledge_base()

    # Restore persisted pipeline state so a restart doesn't lose progress.
    try:
        store.init_db()
        saved = store.load_session()
        if saved:
            current_session.update(saved)
            print(f"[Store] Restored session (stage={store.get_stage()}, "
                  f"role={current_session.get('current_role')}, "
                  f"screened={len(current_session.get('screened', []))}).")
        # Repopulate the posting agent's in-memory job registry.
        restored_jobs = store.load_jobs()
        if restored_jobs:
            active_jobs.update(restored_jobs)
            print(f"[Store] Restored {len(restored_jobs)} job(s).")
            # Re-arm the auto-relaxation timers that were lost on restart.
            from agents.posting_agent import reschedule_pending_relaxations
            reschedule_pending_relaxations()
    except Exception as e:
        print(f"[Store] Startup restore warning: {e}")

    # Start the daily interview-reminder scheduler (Phase 2).
    start_reminder_scheduler()

    print("[Server] HR AI Agent v2.0 is ready! Visit http://localhost:8000")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
