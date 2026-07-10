"""
Inbox Agent — inbound email tracking for candidate replies.

WHAT IT DOES
────────────
After interview invites / offer letters go out, candidates reply. This agent
reads the HR Gmail inbox over IMAP (using the same GMAIL_ADDRESS +
GMAIL_APP_PASSWORD already used for sending — no extra OAuth scope needed),
matches messages to known candidates, and uses the LLM to classify each reply:

    confirmed | declined | reschedule | question | other

The classification is returned to the caller so the pipeline can update each
candidate's status (e.g. mark an interview confirmed, or flag a decline that
should trigger the negotiation flow).

Design notes
────────────
- Read-only: never deletes or moves mail. Optionally marks messages seen.
- Stdlib `imaplib` + `email` — no new dependencies.
- Matching is by sender email address against the provided candidate list.
"""
import os
import email
import imaplib
import json
from email.header import decode_header
from datetime import datetime, timedelta
from llm import get_client, MODEL
from dotenv import load_dotenv

load_dotenv()
client = get_client()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
IMAP_HOST = "imap.gmail.com"

VALID_INTENTS = {"confirmed", "declined", "reschedule", "question", "other"}


def _decode(value: str) -> str:
    """Decode a possibly RFC2047-encoded header into a plain string."""
    if not value:
        return ""
    parts = decode_header(value)
    out = ""
    for text, enc in parts:
        if isinstance(text, bytes):
            out += text.decode(enc or "utf-8", errors="ignore")
        else:
            out += text
    return out


def _extract_body(msg: email.message.Message) -> str:
    """Return the plain-text body of an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and \
                    "attachment" not in str(part.get("Content-Disposition", "")):
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(msg.get_content_charset() or "utf-8", errors="ignore") if payload else ""


def _classify_reply(subject: str, body: str) -> dict:
    """Use the LLM to classify a candidate's reply into an intent + summary."""
    prompt = f"""A candidate replied to an interview invitation or offer email.
Classify their reply.

SUBJECT: {subject}
BODY:
{body[:2000]}

Return ONLY valid JSON (no markdown) in this exact shape:
{{
  "intent": "confirmed | declined | reschedule | question | other",
  "summary": "one short sentence describing what they said",
  "suggested_action": "what HR should do next in one short sentence"
}}

Intent meaning:
- confirmed: they accept/confirm the interview or offer
- declined: they reject the interview or offer
- reschedule: they want a different time
- question: they are asking something and need a reply
- other: anything else"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You classify candidate email replies and output ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        data = json.loads(content)
        if data.get("intent") not in VALID_INTENTS:
            data["intent"] = "other"
        return data
    except Exception as e:
        return {"intent": "other", "summary": f"Could not classify: {e}", "suggested_action": "Review manually."}


def check_replies(candidates: list[dict], days_back: int = 7, mark_seen: bool = False) -> dict:
    """
    Scan the HR inbox for replies from the given candidates.

    Args:
        candidates: list of dicts with at least 'email' (and ideally 'name',
                    'candidate_id') — only mail from these addresses is matched.
        days_back:  how many days of inbox history to scan.
        mark_seen:  if True, mark matched messages as read.

    Returns:
        dict: {"status": "...", "replies": [ {candidate_id, name, email,
               subject, intent, summary, suggested_action, received} ], ...}
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return {"status": "not_configured",
                "message": "GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set in .env — cannot read inbox.",
                "replies": []}

    # Build a lookup of candidate email -> candidate record
    by_email = {}
    for c in candidates:
        em = (c.get("email") or "").strip().lower()
        if em:
            by_email[em] = c
    if not by_email:
        return {"status": "no_candidates", "message": "No candidate emails to match against.", "replies": []}

    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST)
        imap.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        imap.select("INBOX")
    except Exception as e:
        return {"status": "error", "message": f"IMAP login failed: {e}", "replies": []}

    replies = []
    try:
        since = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        # Search each candidate address (IMAP OR chaining is fiddly; per-sender is simplest)
        seen_ids = set()
        for em, cand in by_email.items():
            status, data = imap.search(None, f'(FROM "{em}" SINCE {since})')
            if status != "OK" or not data or not data[0]:
                continue
            for num in data[0].split():
                if num in seen_ids:
                    continue
                seen_ids.add(num)
                fetch_flag = "(RFC822)" if mark_seen else "(BODY.PEEK[])"
                st, msg_data = imap.fetch(num, fetch_flag)
                if st != "OK":
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                subject = _decode(msg.get("Subject", ""))
                body = _extract_body(msg)
                cls = _classify_reply(subject, body)
                replies.append({
                    "candidate_id": cand.get("candidate_id", ""),
                    "name": cand.get("name", ""),
                    "email": em,
                    "subject": subject,
                    "received": _decode(msg.get("Date", "")),
                    "intent": cls.get("intent", "other"),
                    "summary": cls.get("summary", ""),
                    "suggested_action": cls.get("suggested_action", ""),
                })
    finally:
        try:
            imap.close()
            imap.logout()
        except Exception:
            pass

    return {
        "status": "ok",
        "scanned_candidates": len(by_email),
        "replies_found": len(replies),
        "replies": sorted(replies, key=lambda r: r.get("received", "")),
    }
