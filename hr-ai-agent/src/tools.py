"""
HR AI Agent Tools — LangChain @tool functions for Nasiko A2A deployment.
Each tool wraps one of the original HR agent capabilities using OpenAI GPT-4o.
"""
import os
import json
import random
from typing import List, Dict, Any
from langchain_core.tools import tool

# Provider-swappable client (OpenAI by default; Groq/Ollama/etc. via LLM_PROVIDER).
from llm_config import get_client, MODEL as _MODEL

_client = get_client()


def _chat(system: str, user: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """Helper: call OpenAI chat completion."""
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


# ═══════════════════════════════════════════════
# 1. JD GENERATOR
# ═══════════════════════════════════════════════
JD_STYLES = [
    "Standard Corporate", "Startup Casual", "Technical Deep-Dive",
    "Creative / Culture-First", "Executive / Leadership"
]

@tool
def generate_job_description(
    job_title: str,
    department: str = "Engineering",
    experience_level: str = "Senior",
    preferred_skills: str = "",
    style: str = "Standard Corporate"
) -> str:
    """
    Generate a compelling, professional Job Description for a role.

    Args:
        job_title: The title of the role, e.g. 'Senior ML Engineer'
        department: Department or team, e.g. 'Engineering', 'Product'
        experience_level: One of Intern, Junior, Mid, Senior, Lead
        preferred_skills: Comma-separated list of preferred skills
        style: One of 'Standard Corporate', 'Startup Casual', 'Technical Deep-Dive', 'Creative / Culture-First', 'Executive / Leadership'
    """
    system_prompt = f"""You are a world-class HR copywriter. Generate a unique, detailed Job Description.
Tone/Style: {style}.
Format using markdown with **bold** headers and bullet points.
Include sections: About the Role, Key Responsibilities, Required Skills, Nice-to-Have, What We Offer, How to Apply."""

    user_prompt = f"""Write a compelling Job Description for:
- Title: {job_title}
- Department: {department}
- Experience Level: {experience_level}
- Preferred Skills: {preferred_skills if preferred_skills else 'Not specified'}

Make every sentence specific and concrete. Do NOT use generic boilerplate."""

    return _chat(system_prompt, user_prompt, temperature=0.9)


# ═══════════════════════════════════════════════
# 2. RESUME SCREENER
# ═══════════════════════════════════════════════
@tool
def screen_resume(job_description: str, resume_text: str) -> str:
    """
    Score and evaluate a candidate's resume against a job description.
    Returns a structured assessment with a score out of 100.

    Args:
        job_description: The full job description text to evaluate against
        resume_text: The candidate's resume text content
    """
    system_prompt = """You are an expert technical recruiter. Evaluate this resume against the JD.
Return a JSON object with these fields:
- name: candidate name
- email: candidate email (or "not provided")
- score: holistic score out of 100
- strengths: list of 3 key strengths
- gaps: list of skill gaps
- reasoning: 2-3 sentence summary of the evaluation

Return ONLY valid JSON, no markdown."""

    user_prompt = f"""JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}

Evaluate this candidate."""

    return _chat(system_prompt, user_prompt, temperature=0.3, max_tokens=1000)


# ═══════════════════════════════════════════════
# 3. INTERVIEW QUESTION GENERATOR
# ═══════════════════════════════════════════════
@tool
def generate_interview_questions(
    job_description: str,
    candidate_summary: str = "",
    candidate_skills: str = ""
) -> str:
    """
    Generate 10 tailored interview questions for a candidate based on a job description.

    Args:
        job_description: The job description to base questions on
        candidate_summary: Brief summary of the candidate's background
        candidate_skills: Comma-separated list of candidate's key skills
    """
    system_prompt = """You are a senior technical interviewer at a top tech company.
Generate exactly 10 interview questions customized to the candidate and role.

For each question, provide:
1. The question itself
2. Why you're asking it (rationale)
3. What a strong answer looks like

Format as a numbered list with clear sections for each question."""

    user_prompt = f"""JOB DESCRIPTION:
{job_description}

CANDIDATE SUMMARY: {candidate_summary if candidate_summary else 'Not provided'}
CANDIDATE SKILLS: {candidate_skills if candidate_skills else 'Not provided'}

Generate 10 tailored interview questions."""

    return _chat(system_prompt, user_prompt, temperature=0.7, max_tokens=3000)


# ═══════════════════════════════════════════════
# 4. OFFER LETTER GENERATOR
# ═══════════════════════════════════════════════
@tool
def generate_offer_letter(
    candidate_name: str,
    role: str,
    salary: str,
    equity: str = "",
    start_date: str = ""
) -> str:
    """
    Generate a professional, FAANG-grade offer letter for a candidate.

    Args:
        candidate_name: Full name of the candidate
        role: Job title being offered
        salary: Base salary (e.g. '$150,000')
        equity: Equity or bonus details (e.g. '10,000 RSUs')
        start_date: Proposed start date
    """
    system_prompt = "You are a top-tier HR Executive at a leading tech company. Write professional, exciting offer letters."

    user_prompt = f"""Write a FAANG-grade Offer Letter with these details:
- Candidate: {candidate_name}
- Role: {role}
- Base Salary: {salary}
- Equity/Bonus: {equity if equity else 'Standard equity package'}
- Start Date: {start_date if start_date else 'To be determined'}

Include:
1. Welcome and excitement
2. Role title and reporting structure
3. Compensation Breakdown
4. Benefits overview
5. Next steps and expiration

Format as a clean, professional letter."""

    return _chat(system_prompt, user_prompt, temperature=0.6, max_tokens=2000)


# ═══════════════════════════════════════════════
# 5. COMPANY HANDBOOK GENERATOR
# ═══════════════════════════════════════════════
@tool
def generate_company_handbook(
    company_name: str,
    core_values: str = "Innovation, Teamwork, Impact",
    perks: str = "Health coverage, PTO, Remote work"
) -> str:
    """
    Generate a comprehensive company handbook for new employees.

    Args:
        company_name: Name of the company
        core_values: Comma-separated core values
        perks: Comma-separated perks and benefits
    """
    system_prompt = "You are the Head of People at a modern tech company. Write inspiring, comprehensive employee handbooks."

    user_prompt = f"""Write a Company Handbook for {company_name}.

Core Values: {core_values}
Key Perks & Benefits: {perks}

Include these sections:
1. Welcome Narrative & History
2. Our Mission & Core Values
3. Culture & Working Principles
4. Comprehensive Perks & Benefits
5. Code of Conduct summary

Format cleanly with headers and bullet points."""

    return _chat(system_prompt, user_prompt, temperature=0.7, max_tokens=3000)


# ═══════════════════════════════════════════════
# 6. HR HELPDESK / POLICY Q&A
# ═══════════════════════════════════════════════
@tool
def answer_hr_query(question: str) -> str:
    """
    Answer employee HR policy questions like a professional HR representative.
    Covers topics like PTO, benefits, work-from-home policy, interview process, etc.

    Args:
        question: The HR-related question from an employee or candidate
    """
    system_prompt = """You are an official HR assistant for a modern tech company.

RULES:
1. Be warm, professional, and concise — aim for 2-4 sentences max.
2. Never guess or make up policies. If unsure, say: "For specific details on this, please email hr@company.com."
3. Use direct, actionable language.
4. For sensitive matters (salary disputes, termination), recommend scheduling a private meeting with HR.
5. Always end with a helpful follow-up like "Is there anything else I can help with?"

Common policies you know about:
- PTO: 20 days annually + 10 public holidays
- Remote work: Hybrid model, 3 days in office, 2 days remote
- Health: Comprehensive medical, dental, vision coverage
- 401k: 4% company match
- Parental leave: 16 weeks paid
- Learning: $2,000 annual learning budget"""

    return _chat(system_prompt, question, temperature=0.3, max_tokens=500)


# ═══════════════════════════════════════════════
# 7. EMAIL DRAFTER
# ═══════════════════════════════════════════════
@tool
def draft_interview_email(
    candidate_name: str,
    candidate_email: str,
    role: str,
    interview_datetime: str,
    meeting_link: str = ""
) -> str:
    """
    Draft a professional interview invitation email for a candidate.

    Args:
        candidate_name: Full name of the candidate
        candidate_email: Email address of the candidate
        role: The role they are interviewing for
        interview_datetime: Date and time of the interview
        meeting_link: Video call link (optional)
    """
    system_prompt = "You are a professional HR coordinator. Draft concise, warm interview invitation emails."

    user_prompt = f"""Draft an interview invitation email:
- To: {candidate_name} ({candidate_email})
- Role: {role}
- Interview Date/Time: {interview_datetime}
- Meeting Link: {meeting_link if meeting_link else 'Will be shared separately'}

Include: greeting, interview details, what to prepare, and sign-off from the HR team."""

    return _chat(system_prompt, user_prompt, temperature=0.5, max_tokens=800)


# ═══════════════════════════════════════════════
# 8. NEGOTIATION HELPER
# ═══════════════════════════════════════════════
@tool
def negotiation_guidance(
    candidate_name: str,
    role: str,
    offered_salary: str,
    candidate_reason: str = ""
) -> str:
    """
    Advise HR on a compensation negotiation when a candidate declines or asks for more.
    Returns likely reasons, a recommended counter, non-salary levers, and a draft reply.

    Args:
        candidate_name: the candidate's name
        role: the role offered
        offered_salary: what was offered, e.g. '$120,000'
        candidate_reason: the candidate's stated reason, if known
    """
    system_prompt = "You are a seasoned Head of Talent advising an HR manager on a compensation negotiation."
    user_prompt = f"""A candidate is pushing back on an offer.
- Candidate: {candidate_name}
- Role: {role}
- Offered salary: {offered_salary}
- Stated reason: {candidate_reason or 'not provided'}

Provide, in clear sections:
1. Likely reasons for the pushback
2. A specific recommended counter-offer or range
3. Non-salary levers (signing bonus, equity, remote flexibility, learning budget, etc.)
4. When to walk away vs keep negotiating
5. A short, warm draft email HR can send to re-open the conversation"""
    return _chat(system_prompt, user_prompt, temperature=0.5, max_tokens=1000)


# ═══════════════════════════════════════════════
# 9. REJECTION EMAIL
# ═══════════════════════════════════════════════
@tool
def draft_rejection_email(candidate_name: str, role: str, gap: str = "") -> str:
    """
    Draft a polite, constructive rejection email for a candidate who was not selected.

    Args:
        candidate_name: the candidate's name
        role: the role they applied for
        gap: optional note on the main gap vs requirements (kept gentle in the email)
    """
    system_prompt = "You are a professional, empathetic HR recruiter who writes kind, constructive rejection emails."
    user_prompt = f"""Write a rejection email:
- Candidate: {candidate_name}
- Role: {role}
- Main gap (mention gently, if provided): {gap or 'not specified'}

Thank them, clearly but kindly say they weren't selected, give one constructive
note, wish them luck, and sign off from the HR team. Plain text, no subject line."""
    return _chat(system_prompt, user_prompt, temperature=0.6, max_tokens=600)
