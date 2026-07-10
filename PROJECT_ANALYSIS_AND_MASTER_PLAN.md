# 🔬 AI HR Automation Platform — Deep Analysis & Master Plan

> **Team:** Ozark · **Platform:** Nasiko (A2A hackathon) · **Analysis date:** 2026-07-10
> This document is the single source of truth for what the project is, its current status, and how to build it into the best possible version.

---

## Table of Contents
1. [What This Project Is](#1-what-this-project-is)
2. [Repo Reality Check](#2-repo-reality-check-clean-this-first)
3. [Architecture](#3-architecture-of-the-real-app-hackathon)
4. [Notebook Vision → Code Status](#4-notebook-vision--code-reality-feature-status)
5. [Gaps, Bugs & Risks](#5-critical-gaps-bugs--risks)
6. [Master Plan (5 Phases)](#6-master-plan-to-build-the-best-version)
7. [Feature Ideas / Differentiators](#7-features-you-could-add-differentiators)
8. [Immediate Next Steps](#8-immediate-next-steps)

---

## 1. What This Project Is

An **AI-powered, end-to-end HR / recruitment automation system** that lets a single HR person drive the *entire* hiring lifecycle: write the job post → collect applicants → screen resumes → schedule interviews → send emails → generate documents → answer employee questions → onboard new hires.

**Nasiko** is the hackathon platform. It defines the **A2A (Agent-to-Agent) protocol** — a JSON-RPC 2.0 standard where agents are Docker containers exposing tools (Python functions with `@tool`), deployed via GitHub or ZIP into the Nasiko registry. The hackathon goal: build an HR agent and deploy it to Nasiko.

### Two distinct deliverables in this repo

| Deliverable | Location | What it is | Purpose |
|---|---|---|---|
| **Full HR platform** | `hackathon/` | FastAPI web app + dashboard with 9 agents | The real product — a working demo you run locally |
| **Nasiko A2A agent** | `hr-ai-agent/` | LangChain agent packaged for Nasiko | The *submission* — a Dockerized agent speaking A2A JSON-RPC |

Reference material Nasiko provided: `agent-template/`, `a2a-translator/`, `sample-weather-agent/`, and `HACKATHON_AGENT_GUIDE.md`.

---

## 2. Repo Reality Check (clean this first)

The repo is **heavily polluted with duplicates**:

- `AI-HR-Automation-Platform/` and `HR-automation-system-/` — **complete nested copies of the entire root repo** (every file duplicated 2–3×).
- `hackathon/hackathon/agents/interview_agent.py` — a stray nested duplicate.
- `__MACOSX/` folders everywhere — macOS zip artifacts (junk).
- `.DS_Store` files tracked in git.
- `main.py:22-23` imports `send_welcome_package` **twice** (harmless but sloppy).

**~60% of tracked files are redundant.** Keep only: `hackathon/` (the app) + `hr-ai-agent/` (the submission) + the Nasiko reference folders + `doc/`.

---

## 3. Architecture of the Real App (`hackathon/`)

```
Browser Dashboard (index.html + app.js + style.css, ~2,800 lines vanilla JS/CSS)
        │  REST / JSON
        ▼
main.py  ── FastAPI, ~25 endpoints, in-memory session state
        │
        ├── jd_agent.py          → GPT-4o, 5 JD styles + relax_jd()
        ├── posting_agent.py     → Telegram Bot API + APScheduler auto-relax
        ├── screening_agent.py   → GPT-4o resume scoring (BERT utils imported)
        ├── interview_agent.py   → GPT-4o → 10 tailored Q&A
        ├── email_agent.py       → Gmail SMTP: draft / send / reject / welcome
        ├── calendar_agent.py    → wraps calendar_service/
        ├── helpdesk_agent.py    → RAG: BERT embeddings over company_faq.txt + GPT-4o
        ├── onboarding_agent.py  → reportlab PDF offer letter + welcome email
        └── document_agent.py    → GPT-4o → HTML offer letters & handbooks
        │
        └── calendar_service/    → real Google Calendar API
             ├── auth.py            OAuth2 + token refresh
             ├── smart_scheduler.py slot-finding, weekends, Indian holidays, TZ-by-city
             ├── calendar_tools.py  CRUD
             ├── reminder_service.py day-of email reminders
             └── graph.py           LangGraph conversational agent (optional)
```

**Tech stack:** Python 3.12 · FastAPI · OpenAI GPT-4o (used everywhere, despite README claiming Groq/Ollama) · sentence-transformers (`all-MiniLM-L6-v2`) for embeddings · Google Calendar API · Gmail SMTP · Telegram Bot API · APScheduler · reportlab.

### The Nasiko A2A agent (`hr-ai-agent/`)
A LangChain `create_tool_calling_agent` (GPT-4o) exposing **7 tools**: `generate_job_description`, `screen_resume`, `generate_interview_questions`, `generate_offer_letter`, `generate_company_handbook`, `answer_hr_query`, `draft_interview_email`. Ships with `Dockerfile`, `docker-compose.yml`, and `AgentCard.json` (protocol 0.2.9).

---

## 4. Notebook Vision → Code Reality (feature status)

The 6 notebook pages in `doc/` lay out the complete vision. Mapping to actual code:

| # | Feature (from notebook) | Status | Notes |
|---|---|---|---|
| 1 | JD generation (customise, requirement/skill) | ✅ Built | 5 styles, randomized structure |
| 2 | HITL approval of JD (approve / regenerate) | 🟡 Partial | Approve exists; "regenerate + suggest other ways" loop not wired |
| 3 | Post JD to Telegram | ✅ Built | HTML formatting, `posting_agent.py` |
| 4 | Agent analyzes JD status → auto-relax on low response | ✅ Built | APScheduler `check_and_relax()`, 48h, threshold=5 |
| 5 | Candidate resume upload → store in DB | 🟡 Partial | Saves to `data/resumes/` folder — **no real database** |
| 6 | Resume shortlisting (BERT) | 🟡 Diverged | Code uses **GPT-4o holistic scoring**, not BERT ranking. BERT only powers helpdesk |
| 7 | Detailed summary + suggestion to HR | ✅ Built | `evaluation_reasoning` per candidate |
| 8 | Interview scheduling (Calendar + Mail) | ✅ Built | Google Calendar, smart slots, invites, auto-schedule-all |
| 9 | Track invite-mail responses | ❌ Missing | No inbound email tracking |
| 10 | Interview-day reminders (HR + candidate) | 🟡 Partial | `reminder_service.py` exists but not auto-triggered |
| 11 | Per-candidate interview Q&A prep | ✅ Built | 10 Qs with rationale + expected answer |
| 12 | Offer letter mail + track → onboard / negotiate | 🟡 Partial | Letter generates; "track → negotiation" branch missing |
| 13 | Onboarding: welcome mail, docs, policies, intro meeting | 🟡 Partial | Welcome email + PDF built; doc *collection* + intro-meeting scheduling missing |
| 14 | Helpdesk chatbot (RAG on company dataset) | ✅ Built | Real BERT RAG over `company_faq.txt` |
| 15 | Spreadsheet / HR database update | ❌ Missing | Not implemented |
| 16 | Supervisor agent / LangGraph multi-agent | ❌ Missing | App is a flat FastAPI router, not a LangGraph supervisor |
| 17 | State tracking (JD→approve→post→…→onboarding) | ❌ Missing | Only ephemeral in-memory `current_session`; lost on restart |
| 18 | Telegram / Gmail / Calendar / Ollama integration | 🟡 Mixed | Telegram/Gmail/Calendar ✅; **Ollama not used** (all OpenAI) |
| 19 | Nasiko A2A deployment | ✅ Built | `hr-ai-agent/` — 7 tools, Docker, AgentCard |
| 20 | Audio / NLP input | ❌ Missing | "text + audio {NLP}" not started |

**Overall completion: ~65–70% of a strong demo; ~40% of the full notebook vision.**

---

## 5. Critical Gaps, Bugs & Risks

### 🔴 Blocking / config
- **`requirements.txt` is broken** — missing `sentence-transformers`, `scikit-learn`, `reportlab`, `beautifulsoup4`, all imported by the code. Screening, helpdesk, onboarding PDFs, and JD scraping crash on a fresh install. **`requirements_complete.txt` is the correct file** — make it canonical.
- **No `.env`, `credentials.json`, or `token.json`** (correctly gitignored) — nothing runs until created. Needs: `OPENAI_API_KEY`, Google OAuth creds, `GMAIL_APP_PASSWORD`, Telegram token + chat ID.
- **README claims Groq / Ollama; code is 100% OpenAI GPT-4o.** Notebook wanted Ollama (local/free). Pick one story.

### 🟡 Architectural
- **No persistence.** `current_session` and `active_jobs` are in-memory dicts — a restart wipes all candidates, jobs, and scheduled relaxations. **#1 fix for credibility.**
- **Not actually "agentic" in the app.** Notebook emphasizes LangGraph supervisor + multi-agent coordination. The real app is a deterministic REST API calling LLMs. Only agentic pieces: `hr-ai-agent/` (LangChain) and optional `calendar_service/graph.py`.
- **Single-user, single-session** — no auth, no multi-recruiter support.

---

## 6. Master Plan to Build the Best Version

Sequenced "make it real" before "make it fancy."

> **Progress:** ✅ Phase 0 done (committed) · ✅ Phase 1 done · ✅ Phase 2 done · ⬜ Phases 3–5 remaining.
> See the "Build Progress Log" at the bottom for details.

### Phase 0 — Hygiene (½ day)
- Delete `AI-HR-Automation-Platform/`, `HR-automation-system-/`, all `__MACOSX/`, `.DS_Store`, nested `hackathon/hackathon/`.
- Make `requirements_complete.txt` the real `requirements.txt`.
- Write a proper `.env.example`. Fix the double import in `main.py`.
- One README that matches reality (OpenAI — or switch to Ollama in Phase 4).

### Phase 1 — Make it real & runnable (2–3 days)
- **Add a database** (SQLite + SQLAlchemy): tables for `jobs`, `candidates`, `applications`, `interviews`, `offers`, `onboarding`. Replace `current_session` / `active_jobs`.
- Implement the **state machine** (notebook page 3): `JD → approved → posted → collecting → screening → shortlisted → interviewing → offer → onboarding`. Persist and display it.
- End-to-end verify the golden path.

### Phase 2 — Close the notebook loop (3–4 days)
- **Inbound tracking**: Gmail API to detect candidate replies / attendance confirmations → update state.
- **Auto reminders**: schedule `reminder_service.py` via APScheduler on interview dates (day-before + day-of to HR *and* candidate).
- **Offer → track → branch**: if declined, trigger a "negotiation helper" agent for HR.
- **Onboarding completion**: document-collection checklist + auto-schedule intro meeting.
- **Spreadsheet / HR DB sync**: push shortlist + statuses to Google Sheets (or DB + CSV export).

### Phase 3 — Make it genuinely agentic (3–5 days) ← *notebook's real ambition*
- Rebuild orchestration as a **LangGraph supervisor**: one supervisor routes to specialist agents (JD, Screening, Scheduling, Onboarding, Helpdesk) with shared persistent state and **HITL interrupts** at approval points.
- Add **LangSmith** for tracing / debugging / eval (strong "we measure our agent" story for judges).

### Phase 4 — Polish & differentiate (2–3 days)
- Switch screening to **hybrid**: BERT embedding pre-filter → GPT-4o deep eval on top-K only (cheaper, faster, matches notebook).
- Optional **Ollama** local-LLM path — abstract the LLM client so OpenAI / Ollama / Groq are swappable via env.
- Analytics dashboard: real funnel from DB, time-to-hire, source breakdown.

### Phase 5 — Ship to Nasiko (1 day)
- Expand `hr-ai-agent/` tools to cover new capabilities, test with the A2A `curl` calls in the guide, `docker build`, deploy via GitHub connect.

---

## 7. Features You Could Add (differentiators)

- **Bias / fairness guardrails** on screening (strip name/gender/age before scoring) — big credibility win for an HR product.
- **Audio input** ("text + audio {NLP}" from notebook) — Whisper for voice queries to the helpdesk.
- **Candidate-facing Telegram chatbot** (two-way) so applicants ask status / questions.
- **JD → multi-platform posting** (LinkedIn etc.), not just Telegram.
- **Interview scorecard agent** — HR pastes notes → structured evaluation + hire recommendation.
- **Duplicate / plagiarism detection** across resumes.
- **Explainable ranking** — show *why* candidate A > B side by side.

---

## 8. Immediate Next Steps

1. **Clean the repo** (Phase 0) — mostly `rm -rf` of duplicate trees + fixing `requirements.txt`.
2. **Create `.env` + get it running** to see the current state end-to-end.
3. **Add SQLite persistence + the state machine** — the single highest-leverage upgrade; directly fulfills notebook page 3.

---

---

## Build Progress Log

### ✅ Phase 0 — Hygiene (committed, `4186118`)
- Deleted duplicate repo trees (`AI-HR-Automation-Platform/`, `HR-automation-system-/`), `__MACOSX/`, `.DS_Store`, nested `hackathon/hackathon/`.
- Fixed `requirements.txt` (added the missing `sentence-transformers`, `scikit-learn`, `reportlab`, `beautifulsoup4`); removed redundant requirements files.
- Added `hackathon/.env.example` (all env vars documented); fixed the double import in `main.py`; corrected the README (OpenAI, not Groq/Ollama); hardened `.gitignore`.

### ✅ Phase 1 — Persistence + state machine
- New `hackathon/store.py` — stdlib `sqlite3` (no ORM, no new deps). Persists the whole session to `data/hr_state.db`; **forward-only** pipeline state machine (`IDLE→JD_DRAFTED→POSTED→COLLECTING→SCREENED→SHORTLISTED→INTERVIEWING→OFFER→ONBOARDING`); job persistence; stage-history audit.
- `main.py` wired additively: `persist(stage=...)` in every mutating endpoint; session + `active_jobs` restored on startup. New endpoints `GET /api/pipeline`, `POST /api/pipeline/reset`; `/api/session` returns `current_stage`.

### ✅ Phase 2 — Close the notebook loop
- **Inbound tracking:** `agents/inbox_agent.py` (IMAP read via app password, LLM classifies replies confirmed/declined/reschedule/question) → `POST /api/inbox/check`, auto-updates offer status.
- **Auto reminders:** `agents/reminder_agent.py` (APScheduler daily job at `REMINDER_HOUR`, wraps existing `send_reminders_for_today`) → `POST /api/reminders/send-today`.
- **Offer → track → branch:** `agents/negotiation_agent.py` + offer tracking in the session → `POST /api/offer/send`, `GET /api/offers`, `POST /api/offer/response`, `POST /api/offer/negotiate`.
- **Onboarding:** document-collection checklist + intro-meeting scheduling in `agents/onboarding_agent.py` → `GET /api/onboarding/checklist`, `POST /api/onboarding/document-received`, `POST /api/onboarding/schedule-intro`.
- **Spreadsheet sync:** `GET /api/export/candidates.csv`.
- Also closed the Phase 1 gap: `posting_agent.reschedule_pending_relaxations()` re-arms auto-relax timers on restart.
- **Verification:** all files AST-parse; pure logic (checklist, store round-trip, CSV export) passes an isolated functional test. LLM/IMAP/calendar paths follow existing patterns but need a live run (deps + `.env`) to confirm end-to-end.

**Remaining:** Phase 3 (LangGraph supervisor + LangSmith), Phase 4 (hybrid BERT+LLM screening, Ollama option, analytics), Phase 5 (ship expanded tools to Nasiko). Frontend UI for the new Phase 2 endpoints is not yet wired.

---

*Generated from a full read of the `hackathon/` and `hr-ai-agent/` codebases cross-referenced against the 6 handwritten notebook pages in `doc/`.*
