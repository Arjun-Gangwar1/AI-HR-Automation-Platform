"""
Screening Agent - LLM-based resume screening and candidate ranking
"""
import os
import json
import uuid
from llm import get_client, MODEL
from utils.bert_utils import get_embedding, compute_similarity
from dotenv import load_dotenv

load_dotenv()
client = get_client()
MAX_SHORTLIST = int(os.getenv("MAX_SHORTLIST", 5))


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
    Screen and rank resumes against a JD using advanced LLM reasoning.
    
    Args:
        resumes: list of {"filename": str, "text": str}
        jd: job description text
    
    Returns:
        Ranked list of candidate dicts with scores and reasoning.
    """
    print(f"[Screening] Evaluating {len(resumes)} resumes with LLM...")
    
    results = []
    for i, resume in enumerate(resumes):
        print(f"[Screening] Processing {i+1}/{len(resumes)}: {resume['filename']}")
        
        # LLM extracts info AND scores in one pass for deep semantic reasoning
        eval_data = evaluate_resume_with_llm(resume["text"], jd)
        
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
            
            # Since LLM gives one holistic score, we map it back to the frontend's expected keys for compatibility
            "bert_score": eval_data.get("final_score", 0),
            "skill_score": eval_data.get("final_score", 0), 
            "project_score": eval_data.get("final_score", 0),
            "final_score": eval_data.get("final_score", 0),
            "shortlisted": False
        })
    
    # Sort by final score descending
    results.sort(key=lambda x: x["final_score"], reverse=True)
    
    print(f"[Screening] Done. Top candidate: {results[0]['name']} ({results[0]['final_score']}/100) " if results else "")
    return results
