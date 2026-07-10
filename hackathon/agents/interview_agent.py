"""
Interview Agent - Generates personalized interview questions
"""
import os
import json
from llm import get_client, MODEL
from dotenv import load_dotenv

load_dotenv()
client = get_client()

def generate_interview_questions(jd: str, candidate_summary: str, candidate_skills: list, candidate_projects: list) -> list:
    """Generate exactly 10 tailored interview questions based on JD and Resume in JSON format."""
    
    projects_text = 'None provided'
    if candidate_projects:
        projects_list = '\n- '.join(candidate_projects)
        projects_text = f'- {projects_list}'
    
    prompt = f"""You are an expert technical recruiter preparing an interviewer for an upcoming interview.
Based on the provided Job Description and Candidate Profile, generate exactly 10 highly personalized interview questions.
Focus on identifying skill gaps, exploring specific projects, and testing cultural/technical fit.

JOB DESCRIPTION:
{jd[:1500]}

CANDIDATE SUMMARY:
{candidate_summary}

CANDIDATE SKILLS:
{', '.join(candidate_skills)}

CANDIDATE PROJECTS:
{projects_text}

Output EXACTLY 10 questions in this strictly valid JSON format, with NO markdown formatting around it:
[
  {{
    "question": "The actual question to ask the candidate.",
    "rationale": "Why ask this? What gap or project does it target?",
    "expected_answer": "What makes a good or bad answer for this question."
  }},
  ...
]
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a professional HR assistant that outputs valid JSON ONLY."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2500
        )
        content = response.choices[0].message.content.strip()
        
        # Strip markdown code blocks if the LLM includes them
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines[-1].startswith("```"): lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        return json.loads(content)
    except Exception as e:
        print(f"[Interview] Questions generation error: {e}")
        return [
            {
                "question": "Could you walk me through your most challenging recent project?",
                "rationale": "Fallback question: AI generation failed.",
                "expected_answer": "Specific details on their contribution, the technical/business challenges, and the outcome."
            }
        ]
