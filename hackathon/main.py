"""
Main FastAPI Server — HR AI Agent Unified Backend
"""
import os
import uuid
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
from utils.pdf_utils import extract_text_from_pdf

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
}

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
    }

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
    print("[Server] HR AI Agent v2.0 is ready! Visit http://localhost:8000")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
