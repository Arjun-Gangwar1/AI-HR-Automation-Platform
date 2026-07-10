"""
Email Agent - Draft and send interview invitation emails via Gmail SMTP,
and send onboarding welcome packages.
"""
import os
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from llm import get_client, MODEL
from dotenv import load_dotenv

load_dotenv()
client = get_client()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


def draft_interview_email(candidate: dict, role: str, interview_time: str, interview_link: str = "") -> str:
    """Use OpenAI to draft a professional interview invitation email."""
    prompt = f"""Draft a professional, warm interview invitation email for:
- Candidate Name: {candidate.get('name', 'Candidate')}
- Role: {role}
- Interview Time: {interview_time}
- Interview Link/Location: {interview_link if interview_link else 'Details will be shared separately'}
- HR Contact Email: {GMAIL_ADDRESS}

The email should:
1. Congratulate them on being shortlisted
2. Confirm the interview time and format
3. Include a brief agenda (30-45 min technical + 15 min culture fit)
4. Ask them to confirm their attendance by replying
5. Be warm, professional, and encouraging
6. Sign off from "HR Team"

Return only the email body (no subject line), using plain text."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a professional HR coordinator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Email drafting failed: {str(e)}")


def draft_welcome_email(candidate: dict, role: str) -> str:
    """Draft an onboarding welcome email for a selected candidate."""
    prompt = f"""Write a warm, exciting welcome email for a newly hired employee:
- Name: {candidate.get('name', 'Team Member')}
- Role: {role}
- HR Contact: {GMAIL_ADDRESS}

Include:
1. Congratulations on joining the team
2. What to expect in their first week (orientation, team intro, setup)
3. Please find attached: offer letter, company handbook, IT setup guide
4. Emergency HR contact info
5. Encouraging, energetic tone

Sign off from "People & Culture Team"
Return only the email body in plain text."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a warm and professional HR manager."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Welcome email drafting failed: {str(e)}")


def draft_rejection_email(candidate: dict, role: str, jd: str) -> str:
    """Draft a constructive, personalized rejection email explaining the gap."""
    prompt = f"""Write a professional and polite rejection email for a candidate who was not shortlisted.
- Candidate Name: {candidate.get('name', 'Candidate')}
- Role Applied For: {role}
- HR Contact Email: {GMAIL_ADDRESS}
- Noticeable Gap: Look closely at their skills: {', '.join(candidate.get('skills', []))} compared to the JD.

The email should:
1. Thank them for their time and interest in the role
2. Clearly but gently state they were not selected to move forward
3. Provide 1-2 constructive, personalized reasons why based on their skills vs the JD (do not be harsh, just mention they may lack X or we went with someone with more Y)
4. Wish them luck in their job search
5. Sign off from "HR Team"

Return only the email body in plain text."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a professional, empathetic HR recruiter."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Rejection email drafting failed: {str(e)}")


def send_email(
    to_email: str,
    subject: str,
    body: str,
    attachments: list[str] = None
) -> bool:
    """Send an email via Gmail SMTP with optional attachments."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[Email] WARNING: Gmail credentials not configured. Email not sent.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Attach files if any
        if attachments:
            for filepath in attachments:
                if os.path.exists(filepath):
                    with open(filepath, "rb") as f:
                        mime_type, _ = mimetypes.guess_type(filepath)
                        maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
                        part = MIMEBase(maintype, subtype)
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f'attachment; filename="{os.path.basename(filepath)}"'
                        )
                        msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())

        print(f"[Email] Sent to {to_email}: {subject}")
        return True

    except Exception as e:
        print(f"[Email] Send failed to {to_email}: {e}")
        raise RuntimeError(f"Email send failed: {str(e)}")


def send_onboarding_email(candidate: dict, role: str) -> bool:
    """Send welcome email with onboarding documents attached."""
    body = draft_welcome_email(candidate, role)
    subject = f"Welcome to the Team, {candidate.get('name', '')}! 🎉 — Your Onboarding Details"
    
    # Attach onboarding documents from data/onboarding_docs/ if they exist
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "data", "onboarding_docs")
    attachments = []
    if os.path.isdir(docs_dir):
        for fname in os.listdir(docs_dir):
            if fname.endswith(".pdf") or fname.endswith(".txt") or fname.endswith(".docx"):
                attachments.append(os.path.join(docs_dir, fname))
    
    to_email = candidate.get("email", "")
    if not to_email:
        raise ValueError("Candidate has no email address")
    
    return send_email(to_email, subject, body, attachments)
