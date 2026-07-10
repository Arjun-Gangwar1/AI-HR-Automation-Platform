"""
Negotiation Agent — helps HR when a candidate declines or wants to negotiate.

When a candidate rejects an offer (or asks for more), this agent gives the HR
person concrete, strategic guidance: likely reasons, a recommended counter
range, non-salary levers to pull, and a ready-to-send response email draft.
It never auto-sends anything — it's an advisory tool for the human.
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def negotiation_guidance(
    candidate: dict,
    role: str,
    offered_salary: str,
    candidate_reason: str = "",
) -> dict:
    """
    Produce negotiation guidance for HR after a candidate declines / pushes back.

    Args:
        candidate: dict with name/skills/summary (as produced by screening)
        role: the role offered
        offered_salary: what was offered (e.g. "$120,000")
        candidate_reason: the candidate's stated reason, if known

    Returns:
        dict with strategy fields + a draft response email.
    """
    skills = ", ".join(candidate.get("skills", [])) or "not specified"
    name = candidate.get("name", "the candidate")
    summary = candidate.get("summary", "")

    prompt = f"""You are a seasoned Head of Talent advising an HR manager on a
compensation negotiation. A candidate has declined or is pushing back on an offer.

CANDIDATE: {name}
ROLE: {role}
OFFERED SALARY: {offered_salary}
CANDIDATE STRENGTHS: {skills}
CANDIDATE SUMMARY: {summary}
CANDIDATE'S STATED REASON (may be blank): {candidate_reason or "not provided"}

Give practical, specific guidance. Return ONLY valid JSON (no markdown) shaped exactly:
{{
  "likely_reasons": ["short reason 1", "short reason 2"],
  "recommended_counter": "a specific counter-offer or range, with brief justification",
  "non_salary_levers": ["e.g. signing bonus", "equity", "remote flexibility", "learning budget"],
  "walk_away_advice": "one sentence on when HR should walk away vs keep negotiating",
  "response_email": "a warm, professional email body HR can send to re-open the conversation (plain text, no subject line)"
}}"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert compensation negotiator. Output ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=1200,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        return json.loads(content)
    except Exception as e:
        return {
            "likely_reasons": ["Could not generate guidance automatically."],
            "recommended_counter": "",
            "non_salary_levers": [],
            "walk_away_advice": "",
            "response_email": "",
            "error": str(e),
        }
