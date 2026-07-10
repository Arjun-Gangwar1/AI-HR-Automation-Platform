import os
from llm import get_client, MODEL
from dotenv import load_dotenv

load_dotenv()
client = get_client()

def generate_offer_letter(candidate_name: str, role: str, salary: str, equity: str, start_date: str) -> str:
    """Generate a FAANG-grade offer letter in HTML format."""
    prompt = f"""You are a top-tier HR Executive at a leading tech company.
Write a highly professional, exciting, and welcoming FAANG-grade Offer Letter.

Details:
- Candidate Name: {candidate_name}
- Role: {role}
- Base Salary: {salary}
- Equity/Bonus: {equity}
- Start Date: {start_date}

Format the output strictly as beautifully styled HTML (using inline CSS for a pristine, corporate look).
Include sections for:
1. Welcome and excitement to have them join
2. Role title and reporting structure
3. Compensation Breakdown (Base + Equity)
4. Standard Benefits overview
5. Next Steps & Expiration Date

Do not include ```html or any markdown blocks. Output only the raw HTML.
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a professional HR assistant that outputs valid HTML ONLY."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=2500
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines[-1].startswith("```"): lines = lines[:-1]
            content = "\n".join(lines).strip()
        return content
    except Exception as e:
        print(f"[Document] Offer letter generation error: {e}")
        return f"<h3>Error generating offer letter: {e}</h3>"

def generate_company_handbook(company_name: str, core_values: str, perks: str) -> str:
    """Generate a modern Company Handbook in HTML format."""
    prompt = f"""You are the Head of People at a modern, high-growth tech company.
Write a comprehensive, inspiring Company Handbook for new employees.

Details:
- Company Name: {company_name}
- Core Values: {core_values}
- Key Perks & Benefits: {perks}

Format the output strictly as beautifully styled HTML (using inline CSS for a clean, modern look).
Include the following sections:
1. Welcome Narrative & History
2. Our Mission & Core Values (elaborate on the provided values)
3. Culture & Working Principles (communication, flexibility, feedback)
4. Comprehensive Perks & Benefits (elaborate on the provided perks)
5. Code of Conduct summary

Do not include ```html or any markdown blocks. Output only the raw HTML.
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a professional HR assistant that outputs valid HTML ONLY."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines[-1].startswith("```"): lines = lines[:-1]
            content = "\n".join(lines).strip()
        return content
    except Exception as e:
        print(f"[Document] Handbook generation error: {e}")
        return f"<h3>Error generating handbook: {e}</h3>"
