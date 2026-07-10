"""
JD Agent - Generate diverse, high-quality Job Descriptions using Groq LLM
Supports 5 different JD styles and randomized structure
"""
import os
import random
import requests
from bs4 import BeautifulSoup
from llm import get_client, MODEL
from dotenv import load_dotenv

load_dotenv()
client = get_client()

# ---------- JD Styles ----------
JD_STYLES = {
    "standard": {
        "label": "Standard Corporate",
        "tone": "Professional, formal, corporate. Use structured headers and clear bullet points.",
        "opening": "Open with a strong, authoritative statement about the company's mission and the impact of this role.",
    },
    "startup": {
        "label": "Startup Casual",
        "tone": "Casual, energetic, exciting. Use emojis sparingly. Sound like a cool startup, not a corporation.",
        "opening": "Open with a bold, exciting hook about why this role is a once-in-a-lifetime opportunity.",
    },
    "technical": {
        "label": "Technical Deep-Dive",
        "tone": "Highly technical, precise, engineer-to-engineer. Mention specific frameworks, tools, and system design challenges.",
        "opening": "Open by describing a hard, interesting technical problem this person will solve on day one.",
    },
    "culture": {
        "label": "Creative / Culture-First",
        "tone": "Warm, human, values-driven. Emphasize people, belonging, impact on society, and personal growth.",
        "opening": "Open with a story or a value statement about what it means to work here as a human being.",
    },
    "executive": {
        "label": "Executive / Leadership",
        "tone": "Strategic, high-level, visionary. Focus on business impact, P&L ownership, team building, and market positioning.",
        "opening": "Open by describing the strategic business challenge and the leadership opportunity.",
    },
}

# ---------- Randomized section pools ----------
EXTRA_SECTIONS = [
    "**🗓️ A Day in the Life**\nDescribe a realistic day for someone in this role, from morning stand-up to deep work to collaboration.",
    "**🛠️ Tech Stack & Tools**\nList the specific technologies, frameworks, and tools this person will use daily.",
    "**🤔 Why This Role Exists**\nExplain the business or team need that created this opening — give context on the 'why'.",
    "**👥 Team You'll Join**\nDescribe the team: size, backgrounds, working style, who they'll report to, and cross-functional partners.",
    "**📈 Growth Path**\nDescribe career progression: what does 6 months, 1 year, and 3 years look like in this role?",
    "**🌟 Impact Statement**\nDescribe the tangible, measurable impact this person will have on the company and its users/customers.",
    "**🏆 Recent Wins**\nShare 2-3 recent achievements of the team that this person will join and build upon.",
]

SECTION_ORDERINGS = [
    ["About the Role", "Key Responsibilities", "Required Skills", "Nice-to-Have", "What We Offer", "How to Apply"],
    ["Why This Role Matters", "Key Responsibilities", "Required Skills", "What We Offer", "Nice-to-Have", "How to Apply"],
    ["About the Team", "Impact & Responsibilities", "What You Bring", "Bonus Skills", "Perks & Benefits", "Apply Now"],
    ["The Opportunity", "What You'll Do", "Who You Are", "Nice-to-Haves", "Why Join Us", "How to Apply"],
    ["Your Mission", "Day-to-Day", "What We're Looking For", "Bonus Points", "What's In It For You", "Next Steps"],
]


def scrape_url(url: str) -> str:
    """Scrape and return visible text from a URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove scripts and styles
        for ele in soup(["script", "style"]):
            ele.extract()
        text = soup.get_text(separator=' ')
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text[:3000] # Limit to 3000 chars to save tokens
    except Exception as e:
        print(f"[JD Scraper] Failed to scrape {url}: {e}")
        return ""


def _build_prompt(prefs: dict) -> tuple[str, str]:
    """Build system and user prompts for JD generation using the new 5-step preferences."""
    style = prefs.get("style", "Standard Corporate")
    
    # Randomly pick section ordering
    sections = random.choice(SECTION_ORDERINGS)
    section_list = "\n".join(f"{i+1}. **{s}**" for i, s in enumerate(sections))
    
    lead_with = random.choice([
        "company mission",
        "role impact",
        "team description",
        "a day in the life"
    ])
    
    # Unpack preferences cleanly
    title = prefs.get("title", "")
    dept = prefs.get("department", "")
    exp = prefs.get("experience_level", "")
    pref_skills = prefs.get("preferred_skills", "")
    req_nice = prefs.get("required_vs_nice", "")
    excl = prefs.get("excluded_skills", "")
    types = ", ".join(prefs.get("candidate_types", []))
    modes = ", ".join(prefs.get("work_modes", []))
    notice = ", ".join(prefs.get("notice_periods", []))
    projects = prefs.get("project_preferences", "")
    domains = prefs.get("domain_preferences", "")

    system_prompt = f"""You are a world-class HR copywriter who writes original, compelling job descriptions.

CRITICAL INSTRUCTIONS:
Generate a unique, detailed Job Description. Do NOT use generic boilerplate. Vary the structure. Lead with {lead_with}. Make every sentence specific and concrete.

USER PREFERENCES TO INCORPORATE:
- Role details: {title} in {dept} ({exp} level)
- Strongly preferred skills: {pref_skills}
- Required vs nice-to-have clearly labeled: {req_nice}
- EXCLUDED SKILLS (do NOT mention these anywhere): {excl}
- Preferred candidate types: {types}
- Work mode & Notice: {modes} / Notice: {notice}
- Preferred project backgrounds: {projects}
- Domain preferences: {domains}
- Tone/style: {style}.
 
Format using markdown with **bold** headers and bullet points."""
    
    user_prompt = f"Write a compelling, original Job Description for: {title} based on the preferences provided."
    
    return system_prompt, user_prompt


def generate_jd(prefs: dict) -> str:
    """Generate a structured Job Description based on a dictionary of preferences."""
    system_prompt, user_prompt = _build_prompt(prefs)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.9,
            max_tokens=2000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"JD generation failed: {str(e)}")


def get_styles() -> dict:
    """Return available JD styles for the frontend."""
    return {k: v["label"] for k, v in JD_STYLES.items()}


def relax_jd(original_jd: str, reason: str = "low application count") -> str:
    """Relax/broaden an existing JD to attract more applicants."""
    try:
        prompt = f"""The following Job Description has received very few applications ({reason}).
Please rewrite it with slightly relaxed requirements to attract more candidates:
- Reduce required years of experience by 1-2 years
- Convert 2-3 "required" skills to "nice-to-have"
- Make the language more welcoming and inclusive
- Keep the core role and responsibilities unchanged

Original JD:
{original_jd}

Return only the updated JD, no explanation needed."""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are an expert HR recruiter."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=2000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"JD relaxation failed: {str(e)}")
