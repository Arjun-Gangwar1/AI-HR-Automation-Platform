"""
orchestrator.py — LangGraph HR Supervisor Agent (Phase 3).

WHAT THIS IS
────────────
The dashboard drives each agent through explicit REST endpoints (deterministic,
button-per-step). This module adds the *agentic* layer the notebook envisions: a
single supervisor "brain" (a LangGraph ReAct agent) that reads a natural-language
request from HR, decides which specialist capability to use, calls it as a tool,
and can chain several in one turn — e.g. "Draft a JD for a senior ML engineer,
then give me 10 interview questions for a candidate who's done RAG work."

It reuses the SAME underlying agent functions the REST API uses (no duplicate
prompt logic) and the SAME LLM provider (free Groq via llm.get_langchain_llm).

LangSmith tracing is automatic when these env vars are set (no code needed):
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=ls-...
    LANGCHAIN_PROJECT=hr-ai-supervisor
"""
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from llm import get_langchain_llm, PROVIDER, MODEL

# Reuse the real specialist agents (same code the REST endpoints call).
from agents.jd_agent import generate_jd
from agents.screening_agent import evaluate_resume_with_llm
from agents.interview_agent import generate_interview_questions as _gen_questions
from agents.email_agent import draft_interview_email as _draft_email
from agents.helpdesk_agent import answer_query, load_knowledge_base
from agents.document_agent import generate_offer_letter as _gen_offer
from agents.negotiation_agent import negotiation_guidance as _negotiate
import store


# ══════════════════════════════════════════════════════════════
# TOOLS — each wraps one specialist capability
# ══════════════════════════════════════════════════════════════

@tool
def generate_job_description(title: str, experience_level: str = "Senior",
                             preferred_skills: str = "", style: str = "Standard Corporate") -> str:
    """Generate a full job description. Use when HR asks to write/create/draft a JD or job posting.

    Args:
        title: the role title, e.g. 'Senior Machine Learning Engineer'
        experience_level: Intern, Junior, Mid, Senior, or Lead
        preferred_skills: comma-separated key skills
        style: one of Standard Corporate, Startup Casual, Technical Deep-Dive, Culture-First, Executive
    """
    return generate_jd({
        "title": title, "experience_level": experience_level,
        "preferred_skills": preferred_skills, "style": style,
    })


@tool
def score_resume(job_description: str, resume_text: str) -> str:
    """Evaluate ONE candidate's resume against a job description and return a score + reasoning.
    Use when HR pastes a resume and asks how well it fits, or to screen a candidate.

    Args:
        job_description: the JD text to evaluate against
        resume_text: the candidate's resume text
    """
    d = evaluate_resume_with_llm(resume_text, job_description)
    return (f"Candidate: {d.get('name','?')} | Score: {d.get('final_score',0)}/100\n"
            f"Skills: {', '.join(d.get('skills', []))}\n"
            f"Assessment: {d.get('evaluation_reasoning','')}")


@tool
def interview_questions(job_description: str, candidate_summary: str = "",
                        candidate_skills: str = "") -> str:
    """Generate tailored interview questions for a candidate. Use when HR asks for
    interview questions / an interview kit for a role or candidate.

    Args:
        job_description: the role's JD
        candidate_summary: brief background of the candidate
        candidate_skills: comma-separated skills
    """
    skills = [s.strip() for s in candidate_skills.split(",") if s.strip()]
    qs = _gen_questions(job_description, candidate_summary, skills, [])
    return "\n\n".join(
        f"{i+1}. {q.get('question','')}\n   Why: {q.get('rationale','')}"
        for i, q in enumerate(qs)
    )


@tool
def draft_interview_invite(candidate_name: str, role: str,
                           interview_time: str, meeting_link: str = "") -> str:
    """Draft a professional interview invitation email. Use when HR asks to write an
    interview invite / email to a candidate.

    Args:
        candidate_name: candidate's name
        role: role they're interviewing for
        interview_time: date/time of the interview
        meeting_link: optional video link
    """
    return _draft_email({"name": candidate_name}, role, interview_time, meeting_link)


@tool
def answer_hr_policy(question: str) -> str:
    """Answer an HR policy / company FAQ question using the company knowledge base (RAG).
    Use for questions about leave, benefits, WFH, interview process, etc.

    Args:
        question: the employee/candidate's HR question
    """
    return answer_query(question)


@tool
def create_offer_letter(candidate_name: str, role: str, salary: str,
                        equity: str = "", start_date: str = "") -> str:
    """Generate a formal offer letter (returns HTML). Use when HR asks to create/draft an offer letter.

    Args:
        candidate_name: candidate's full name
        role: role being offered
        salary: base salary, e.g. '$150,000'
        equity: equity/bonus details
        start_date: proposed start date
    """
    html = _gen_offer(candidate_name, role, salary, equity, start_date)
    return f"Offer letter generated ({len(html)} chars of HTML). Preview:\n" + html[:600]


@tool
def negotiation_help(candidate_name: str, role: str, offered_salary: str, reason: str = "") -> str:
    """Get negotiation guidance when a candidate declines or pushes back on an offer.
    Use when HR mentions a candidate wants more money / rejected the offer / is negotiating.

    Args:
        candidate_name: candidate's name
        role: the role offered
        offered_salary: what was offered
        reason: the candidate's stated reason, if known
    """
    g = _negotiate({"name": candidate_name}, role, offered_salary, reason)
    return (f"Likely reasons: {'; '.join(g.get('likely_reasons', []))}\n"
            f"Recommended counter: {g.get('recommended_counter','')}\n"
            f"Non-salary levers: {'; '.join(g.get('non_salary_levers', []))}\n"
            f"Walk-away advice: {g.get('walk_away_advice','')}")


@tool
def pipeline_status() -> str:
    """Report where the current hiring pipeline stands (which stage). Use when HR asks
    'where are we', 'what's the status', or about the current recruitment stage."""
    stage = store.get_stage()
    return f"Current pipeline stage: {stage} ({store.STAGE_LABELS.get(stage, stage)})."


HR_TOOLS = [
    generate_job_description, score_resume, interview_questions,
    draft_interview_invite, answer_hr_policy, create_offer_letter,
    negotiation_help, pipeline_status,
]

SUPERVISOR_PROMPT = """You are the HR Supervisor — an intelligent hiring assistant that \
coordinates a team of specialist HR tools across the full recruitment lifecycle: writing \
job descriptions, screening resumes, preparing interview questions, drafting emails, \
answering HR policy questions, creating offer letters, and advising on negotiations.

Guidelines:
- Understand the HR user's intent, then call the most appropriate tool(s). You may chain \
several tools in one turn to fully answer a request.
- Ask a brief clarifying question only if a required detail is genuinely missing.
- Be concise and professional. Summarize tool results clearly for a busy recruiter.
- For anything you don't have a tool for, answer helpfully from general HR knowledge and \
say so."""


_agent = None


def get_supervisor():
    """Build (once) and return the compiled LangGraph supervisor agent."""
    global _agent
    if _agent is None:
        # Ensure the helpdesk knowledge base is available for answer_hr_policy.
        try:
            load_knowledge_base()
        except Exception:
            pass
        llm = get_langchain_llm(temperature=0.2)
        _agent = create_react_agent(llm, HR_TOOLS, prompt=SUPERVISOR_PROMPT)
    return _agent


def run_supervisor(message: str, history: list[dict] | None = None) -> dict:
    """
    Run one turn of the supervisor.

    Args:
        message: the HR user's message.
        history: optional prior messages as [{"role": "user"|"assistant", "content": str}].

    Returns:
        dict with the assistant reply text and the list of tools invoked.
    """
    agent = get_supervisor()
    msgs = []
    for m in (history or []):
        role = m.get("role")
        if role in ("user", "assistant") and m.get("content"):
            msgs.append((role, m["content"]))
    msgs.append(("user", message))

    try:
        result = agent.invoke({"messages": msgs})
    except Exception as e:
        detail = str(e)
        if "rate_limit" in detail or "429" in detail:
            friendly = ("The free LLM provider hit its rate/token limit. Wait a few minutes, "
                        "switch LLM_PROVIDER/LLM_MODEL in .env, or use OpenAI.")
        elif "tool_use_failed" in detail:
            friendly = ("The current model struggled to format a tool call. Use a stronger "
                        "tool-calling model (e.g. Groq llama-3.3-70b or OpenAI gpt-4o).")
        else:
            friendly = f"Supervisor error: {detail[:300]}"
        return {"reply": friendly, "tools_used": [], "provider": PROVIDER, "model": MODEL, "error": True}

    out_msgs = result.get("messages", [])

    # Collect which tools were called (for transparency in the UI).
    tools_used = []
    for m in out_msgs:
        for tc in (getattr(m, "tool_calls", None) or []):
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
            if name:
                tools_used.append(name)

    reply = out_msgs[-1].content if out_msgs else ""
    return {"reply": reply, "tools_used": tools_used, "provider": PROVIDER, "model": MODEL}
