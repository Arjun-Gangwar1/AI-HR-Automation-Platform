"""
Screening Agent - Hybrid resume screening (BERT pre-filter + LLM deep-eval).

Stage 1 (cheap, local): rank ALL resumes by BERT semantic similarity to the JD.
Stage 2 (expensive, LLM): run the full GPT/Groq evaluation only on the top-K.

This keeps screening fast and token-cheap on large batches (the LLM ran on every
resume before), while still giving deep, reasoned scores to the promising ones.
"""
import os
import re
import json
import uuid
from llm import get_client, MODEL
from utils.bert_utils import get_embedding, compute_similarity
from dotenv import load_dotenv

load_dotenv()
client = get_client()
MAX_SHORTLIST = int(os.getenv("MAX_SHORTLIST", 5))
# How many top BERT-ranked resumes get the expensive LLM deep-eval.
SCREEN_LLM_TOP_K = int(os.getenv("SCREEN_LLM_TOP_K", max(MAX_SHORTLIST, 5)))

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(\+?\d[\d\s\-]{7,}\d)")


def _quick_extract(text: str, filename: str) -> dict:
    """Cheap regex extraction of name/email/phone for pre-screened (non-LLM) resumes."""
    email_m = _EMAIL_RE.search(text)
    phone_m = _PHONE_RE.search(text)
    name = ""
    for line in text.splitlines():
        s = line.strip()
        if s and "@" not in s and not _PHONE_RE.search(s) and 2 < len(s) and len(s.split()) <= 5:
            name = s
            break
    if not name:
        name = os.path.splitext(os.path.basename(filename))[0].replace("_", " ").title()
    return {
        "name": name,
        "email": email_m.group(0) if email_m else "",
        "phone": phone_m.group(0).strip() if phone_m else "",
    }


def evaluate_resume_with_llm(resume_text: str, jd_text: str) -> dict:
    """Use LLM to extract info and evaluate the resume against the JD."""
    prompt = f"""You are an expert technical recruiter evaluating a candidate's resume against a Job Description (JD).
    
Job Description:
---
{jd_text[:3000]}
---

Candidate's Resume:
---
{resume_text[:4000]}
---

Analyze the resume and evaluate how well the candidate fits the JD. Extract their details and provide a score from 0 to 100 based on their semantic fit (skills, experience, project relevance).

Return your analysis in the following strict JSON format, and NOTHING ELSE. Do not include markdown blocks or any other text before or after the JSON.
{{
  "name": "Candidate Full Name",
  "email": "Email address if found, else empty",
  "phone": "Phone number if found, else empty",
  "skills": ["Skill 1", "Skill 2"],
  "projects": ["Brief project 1", "Brief project 2"],
  "experience_years": <integer number of years>,
  "education": "Highest degree or university",
  "summary": "1-2 sentence professional summary",
  "evaluation_reasoning": "A paragraph explaining why they are or are not a good fit, highlighting strengths and missing requirements.",
  "final_score": <integer from 0 to 100>
}}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a professional HR evaluation system that outputs ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        content = response.choices[0].message.content.strip()
        
        # Strip markdown json block if the LLM adds it despite instructions
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines[-1].startswith("```"): lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        return json.loads(content)
    except Exception as e:
        print(f"[Screening] LLM evaluation error: {e}")
        # Fallback dictionary if parsing fails
        return {
            "name": "Unknown (Parsing Error)",
            "email": "",
            "phone": "",
            "skills": [],
            "projects": [],
            "experience_years": 0,
            "education": "",
            "summary": "Could not parse resume completely.",
            "evaluation_reasoning": f"Error during AI evaluation: {str(e)}",
            "final_score": 0
        }


def screen_resumes(resumes: list[dict], jd: str) -> list[dict]:
    """
    Hybrid screen + rank resumes against a JD.

    Stage 1: BERT semantic similarity for ALL resumes (fast, local, free).
    Stage 2: full LLM deep-eval for the top-K only (deep reasoning where it matters).

    Args:
        resumes: list of {"filename": str, "text": str}
        jd: job description text

    Returns:
        Ranked list of candidate dicts with scores and reasoning.
    """
    n = len(resumes)
    print(f"[Screening] Stage 1 — BERT pre-filter of {n} resumes...")

    jd_emb = get_embedding(jd)
    ranked = []
    for r in resumes:
        sim = compute_similarity(jd_emb, get_embedding(r["text"][:4000]))
        ranked.append((sim, r))
    ranked.sort(key=lambda x: x[0], reverse=True)

    top_k = min(SCREEN_LLM_TOP_K, n)
    print(f"[Screening] Stage 2 — LLM deep-eval of top {top_k}/{n}...")

    results = []
    for rank, (sim, resume) in enumerate(ranked):
        bert_score = int(round(sim * 100))

        if rank < top_k:
            eval_data = evaluate_resume_with_llm(resume["text"], jd)
            llm_score = eval_data.get("final_score", 0)
            results.append({
                "candidate_id": str(uuid.uuid4())[:8],
                "filename": resume["filename"],
                "name": eval_data.get("name", "Unknown"),
                "email": eval_data.get("email", ""),
                "phone": eval_data.get("phone", ""),
                "skills": eval_data.get("skills", []),
                "projects": eval_data.get("projects", []),
                "experience_years": eval_data.get("experience_years", 0),
                "education": eval_data.get("education", ""),
                "summary": eval_data.get("summary", ""),
                "evaluation_reasoning": eval_data.get("evaluation_reasoning", "No reasoning provided."),
                "bert_score": bert_score,          # real semantic similarity
                "skill_score": llm_score,
                "project_score": llm_score,
                "final_score": llm_score,          # LLM holistic score
                "deep_evaluated": True,
                "shortlisted": False,
            })
        else:
            q = _quick_extract(resume["text"], resume["filename"])
            results.append({
                "candidate_id": str(uuid.uuid4())[:8],
                "filename": resume["filename"],
                "name": q["name"],
                "email": q["email"],
                "phone": q["phone"],
                "skills": [],
                "projects": [],
                "experience_years": 0,
                "education": "",
                "summary": "Pre-screened by semantic similarity (not deeply evaluated).",
                "evaluation_reasoning": (
                    f"Ranked #{rank + 1} of {n} by BERT similarity to the JD — below the "
                    f"top-{top_k} threshold for deep AI review. Re-run with a higher "
                    f"SCREEN_LLM_TOP_K to deep-evaluate more candidates."
                ),
                "bert_score": bert_score,
                "skill_score": bert_score,
                "project_score": bert_score,
                "final_score": bert_score,
                "deep_evaluated": False,
                "shortlisted": False,
            })

    # Deep-evaluated candidates rank above pre-screened; then by score within each group.
    results.sort(key=lambda x: (x["deep_evaluated"], x["final_score"]), reverse=True)

    if results:
        print(f"[Screening] Done. Top candidate: {results[0]['name']} "
              f"({results[0]['final_score']}/100, deep={results[0]['deep_evaluated']})")
    return results
