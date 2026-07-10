# 📚 AI HR Automation Platform — Complete Master Guide

> **Team:** Ozark · **Platform target:** Nasiko (A2A hackathon) · **Status:** All 5 build phases complete, running free on Groq.
> This is the single, complete reference for the project — what it is, the problem it solves, how it works end‑to‑end, every feature, the full tech stack, how to run and deploy it, and where to take it next.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Problem We're Solving](#2-the-problem-were-solving)
3. [Our Solution — The Big Picture](#3-our-solution--the-big-picture)
4. [What is Nasiko? (and life with vs. without it)](#4-what-is-nasiko-and-life-with-vs-without-it)
5. [System Architecture](#5-system-architecture)
6. [The Recruitment Pipeline (the heart of the system)](#6-the-recruitment-pipeline-the-heart-of-the-system)
7. [The Agents — What Each One Does](#7-the-agents--what-each-one-does)
8. [Complete Feature Catalog](#8-complete-feature-catalog)
9. [How the Key Pieces Actually Work (deep dives)](#9-how-the-key-pieces-actually-work-deep-dives)
10. [Full Tech Stack](#10-full-tech-stack)
11. [Configuration & Tunable Factors](#11-configuration--tunable-factors)
12. [API Reference](#12-api-reference)
13. [From Idea to Build — The Journey](#13-from-idea-to-build--the-journey)
14. [Setup & Running It Yourself](#14-setup--running-it-yourself)
15. [Deployment — With Nasiko and Without](#15-deployment--with-nasiko-and-without)
16. [Security & Privacy](#16-security--privacy)
17. [Known Limitations](#17-known-limitations)
18. [What More We Can Do (Roadmap)](#18-what-more-we-can-do-roadmap)
19. [Glossary](#19-glossary)

---

## 1. Executive Summary

The **AI HR Automation Platform** is an end‑to‑end system that lets **one HR person run the entire hiring lifecycle** — from writing the job post to onboarding the new hire — with AI doing the heavy lifting at every step.

It exists in **two forms**:

- **The full product** (`hackathon/`) — a FastAPI web app + dashboard where a recruiter clicks through the whole flow: generate a job description → post it → screen resumes → shortlist → schedule interviews → send emails → make offers → onboard. It has a **restart‑safe pipeline**, an **AI "Supervisor" chat** that can drive tools in plain English, and a **live analytics** view.
- **The Nasiko submission** (`hr-ai-agent/`) — a Dockerized, protocol‑compliant AI agent that packages the same HR capabilities as **9 callable tools** and speaks the **A2A (Agent‑to‑Agent) JSON‑RPC protocol** so it can be deployed into the Nasiko agent registry.

It runs **completely free** on Groq's LLM API (with a one‑line switch to OpenAI, Ollama, Gemini, or OpenRouter), uses **local BERT embeddings** for semantic work, and integrates **Google Calendar, Gmail, and Telegram**.

---

## 2. The Problem We're Solving

Hiring is one of the most **repetitive, time‑consuming, and error‑prone** processes in any company. A single open role forces HR to juggle dozens of manual tasks:

| Pain point | What it looks like today |
|---|---|
| **Writing job descriptions** | Hours per JD, often generic boilerplate that doesn't attract the right people |
| **Low applicant response** | A JD gets posted and… nothing. Nobody notices or adjusts it. |
| **Resume screening** | Reading 50–500 resumes by hand; slow, inconsistent, biased, and exhausting |
| **Interview scheduling** | Endless email back‑and‑forth to find a slot, avoid weekends/holidays, handle timezones |
| **Communication** | Manually drafting invite / rejection / offer / welcome emails, one at a time |
| **Interview prep** | HR walks in without tailored questions for the specific candidate |
| **Offer negotiation** | HR is unsure how to counter when a candidate pushes back |
| **Onboarding** | Chasing documents, sending policies, scheduling intro meetings manually |
| **Employee questions** | HR fields the same "what's the WFH policy?" questions all day |
| **No visibility** | Nobody can answer "where is this role in the pipeline right now?" |

**The core problem:** HR spends most of its time on *low‑value repetitive coordination* instead of *high‑value human judgment*. Everything is manual, disconnected, and has no memory.

---

## 3. Our Solution — The Big Picture

We built an **AI agent system that automates the entire hiring funnel** while keeping a **human in the loop (HITL)** at the decision points that matter.

The philosophy in one line: **AI does the repetitive coordination; the human approves the judgment calls.**

What that means concretely:

- **AI writes** the job description; **HR approves** it before it goes live.
- **AI posts** the job to Telegram and **watches the response**; if too few people apply, it **automatically rewrites (relaxes) the JD** and reposts.
- **AI screens** every resume — fast BERT ranking first, then deep LLM analysis on the best ones — and hands HR a **ranked shortlist with reasoning**.
- **AI finds interview slots** (skipping weekends, Indian holidays, timezone conflicts), **books them on Google Calendar**, and **emails invites**.
- **AI drafts** every email (invite, rejection, offer, welcome); HR confirms before sending.
- **AI prepares** tailored interview questions per candidate.
- **AI advises** on negotiation when a candidate pushes back on an offer.
- **AI tracks** onboarding documents and schedules the intro meeting.
- **A chatbot** answers employee HR‑policy questions from the company knowledge base.
- **An AI Supervisor** lets HR do any of this by just typing a request in plain English.
- **Everything is remembered** — the pipeline state lives in a database and survives restarts.

---

## 4. What is Nasiko? (and life with vs. without it)

### What Nasiko is
**Nasiko** is the **hackathon platform** this project targets. It defines and hosts the **A2A (Agent‑to‑Agent) protocol** — a standard, based on **JSON‑RPC 2.0**, that lets independent AI agents be packaged, deployed, discovered, and called in a uniform way.

On Nasiko, an "agent" is:
- A **Docker container** exposing an HTTP endpoint,
- That accepts a `message/send` JSON‑RPC call,
- Runs its logic (LLM + tools),
- And returns a structured **Task** result with **artifacts** (the answer).

You deploy an agent by **connecting a GitHub repo** or **uploading a ZIP**; Nasiko builds the container and registers it. Each agent ships an **`AgentCard.json`** describing its name, version, and **skills** (its tools).

### Nasiko's role in *our* project
Nasiko is the **destination for our submission** (`hr-ai-agent/`). It is **not** required for the product to work — it's the delivery/hosting layer for the hackathon. Our `hr-ai-agent/` folder is fully A2A‑compliant: `Dockerfile`, `docker-compose.yml`, `AgentCard.json` (v1.1.0, 9 skills), and a JSON‑RPC server on port 5000.

### With Nasiko vs. without Nasiko

| | **With Nasiko** | **Without Nasiko** |
|---|---|---|
| **What you deploy** | `hr-ai-agent/` (the A2A agent) | `hackathon/` (the full web app) |
| **How** | Connect GitHub / Upload ZIP on the Nasiko dashboard | `python main.py` → open `localhost:8000` |
| **Interface** | JSON‑RPC `message/send` (agent‑to‑agent) | Web dashboard + REST API |
| **Who uses it** | Other agents / the Nasiko registry | A human recruiter in the browser |
| **Scope** | 9 stateless HR tools in one conversational agent | The complete stateful pipeline, calendar, analytics, supervisor |

**In short:** *With* Nasiko, our HR agent becomes a reusable building block other agents can call. *Without* Nasiko, we still have a complete, self‑hosted HR platform that runs anywhere Python runs. We built **both** so the project is useful in and out of the hackathon.

---

## 5. System Architecture

### Repository layout (what matters)

```
Nasiko-Ozark/
├── hackathon/                 # ★ THE FULL PRODUCT (web app)
│   ├── main.py                #   FastAPI server, ~30 endpoints
│   ├── llm.py                 #   Swappable LLM provider (OpenAI/Groq/Ollama/…)
│   ├── store.py               #   SQLite persistence + pipeline state machine
│   ├── orchestrator.py        #   LangGraph "AI Supervisor" (8 tools)
│   ├── agents/                #   9 specialist agents (see §7)
│   ├── calendar_service/      #   Google Calendar integration
│   ├── utils/                 #   BERT embeddings + PDF text extraction
│   ├── static/                #   Dashboard UI (index.html, app.js, style.css)
│   ├── data/                  #   FAQ, sample resumes, onboarding docs
│   ├── test_phase2.py         #   One-command smoke test (15 checks)
│   ├── requirements.txt
│   └── .env.example
│
├── hr-ai-agent/               # ★ THE NASIKO SUBMISSION (A2A agent)
│   ├── src/agent.py           #   LangGraph create_react_agent (9 tools)
│   ├── src/tools.py           #   9 @tool functions
│   ├── src/llm_config.py      #   Self-contained provider switch
│   ├── src/__main__.py        #   A2A JSON-RPC server (port 5000)
│   ├── src/models.py          #   A2A protocol pydantic models
│   ├── AgentCard.json         #   Agent metadata (9 skills, v1.1.0)
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── agent-template/            # Nasiko reference example
├── a2a-translator/            # Nasiko reference example
├── sample-weather-agent/      # Nasiko reference example
├── doc/                       # Original handwritten design notes (6 photos)
├── PROJECT_ANALYSIS_AND_MASTER_PLAN.md
└── MASTER_GUIDE.md            # ← this file
```

### The full app's request flow

```
Browser Dashboard  (static/index.html + app.js + style.css)
        │  REST / JSON  (fetch)
        ▼
main.py  (FastAPI)  ── in‑memory session, persisted to SQLite via store.py
        │
        ├─ agents/jd_agent.py          → LLM: write / relax job descriptions
        ├─ agents/posting_agent.py     → Telegram Bot API + APScheduler auto‑relax
        ├─ agents/screening_agent.py   → BERT rank ALL + LLM deep‑eval top‑K
        ├─ agents/interview_agent.py   → LLM: 10 tailored questions
        ├─ agents/email_agent.py       → Gmail SMTP: draft/send invite/reject/welcome
        ├─ agents/calendar_agent.py    → wraps calendar_service/
        ├─ agents/helpdesk_agent.py    → RAG: BERT over FAQ + LLM answer
        ├─ agents/onboarding_agent.py  → PDF offer letter + checklist + intro meeting
        ├─ agents/document_agent.py    → LLM: HTML offer letters & handbooks
        ├─ agents/inbox_agent.py       → IMAP read + LLM classify candidate replies
        ├─ agents/negotiation_agent.py → LLM: counter‑offer guidance
        ├─ orchestrator.py             → LangGraph Supervisor (routes to the above)
        │
        ├─ store.py                    → SQLite: session, jobs, stage history
        ├─ llm.py                      → one place to pick the LLM provider
        └─ calendar_service/
             ├─ auth.py                → Google OAuth2 + token refresh
             ├─ smart_scheduler.py     → slot finding, holidays, timezones
             ├─ calendar_tools.py      → event CRUD
             └─ reminder_service.py    → day‑of email reminders (Gmail API)
```

---

## 6. The Recruitment Pipeline (the heart of the system)

Everything revolves around a **9‑stage state machine** (from the original design notes). It is **forward‑only** (progress never rewinds) and **persisted in SQLite**, so a server restart resumes exactly where you left off.

```
IDLE → JD_DRAFTED → POSTED → COLLECTING → SCREENED → SHORTLISTED → INTERVIEWING → OFFER → ONBOARDING
```

| Stage | Meaning | Triggered by |
|---|---|---|
| **IDLE** | Nothing started | fresh session / reset |
| **JD_DRAFTED** | A job description exists | `generate-jd` |
| **POSTED** | JD approved & posted to Telegram | `post-jd` |
| **COLLECTING** | Resumes are coming in | `upload-resumes` |
| **SCREENED** | Resumes scored & ranked | `screen-resumes` |
| **SHORTLISTED** | HR picked the finalists | `shortlist` |
| **INTERVIEWING** | Invites drafted/sent, slots booked | `draft-emails` / `send-emails` / auto‑schedule |
| **OFFER** | Offer letter generated / sent | `offer/send`, `documents/offer-letter` |
| **ONBOARDING** | Welcome package + docs + intro meeting | `onboard`, `onboarding/*` |

The **Pipeline page** in the dashboard shows this as a live progress bar with a timestamped history. `GET /api/pipeline` returns it as JSON.

**Why this matters:** it turns a pile of disconnected actions into a *tracked, resumable process* — you can always answer "where is this role right now?"

---

## 7. The Agents — What Each One Does

Each agent is a focused Python module. "Agent" here means *a specialist capability*, not a separate running process.

| Agent | File | Job | AI used |
|---|---|---|---|
| **JD Agent** | `jd_agent.py` | Write job descriptions in 5 styles; **relax** a JD to attract more applicants; can scrape a reference URL | LLM |
| **Posting Agent** | `posting_agent.py` | Post JD to Telegram; **auto‑relax** on low response (APScheduler, every 48h) | LLM + Telegram API |
| **Screening Agent** | `screening_agent.py` | **Hybrid**: BERT ranks all resumes, LLM deeply evaluates the top‑K; returns scores + reasoning | BERT + LLM |
| **Interview Agent** | `interview_agent.py` | Generate 10 tailored questions per candidate (with rationale + expected answer) | LLM |
| **Email Agent** | `email_agent.py` | Draft & send interview / rejection / welcome emails via Gmail SMTP | LLM + SMTP |
| **Calendar Agent** | `calendar_agent.py` | Create/read/delete events; smart‑schedule single or all shortlisted candidates | Google Calendar |
| **Helpdesk Agent** | `helpdesk_agent.py` | RAG chatbot: answers HR‑policy questions grounded in the company FAQ | BERT (RAG) + LLM |
| **Onboarding Agent** | `onboarding_agent.py` | Welcome package + PDF offer letter; **document checklist**; **schedule intro meeting** | LLM + reportlab + Calendar |
| **Document Agent** | `document_agent.py` | Generate polished HTML offer letters & company handbooks | LLM |
| **Inbox Agent** | `inbox_agent.py` | Read the HR inbox (IMAP), **classify replies** (confirmed / declined / reschedule / question) | IMAP + LLM |
| **Negotiation Agent** | `negotiation_agent.py` | Advise HR on counter‑offers, non‑salary levers, and a reply draft | LLM |
| **Supervisor** | `orchestrator.py` | **LangGraph agent** that reads plain English and routes to the right tool(s), chaining several in one turn | LangGraph + LLM |

---

## 8. Complete Feature Catalog

### Recruitment
- **JD Generator** — 5 styles (Corporate, Startup, Technical, Culture‑First, Executive), randomized structure so no two JDs look templated, exclusion of unwanted skills, 5‑step wizard UI.
- **Auto JD Relaxation** — if a posted JD gets fewer than a threshold of applications within N hours, the system rewrites it looser and reposts automatically.
- **Multi‑channel Posting** — Telegram out of the box (extensible).
- **Hybrid Resume Screening** — BERT semantic ranking of *all* resumes + deep LLM evaluation of the top‑K (fast, cheap, explainable). Cards show 🧠 deep vs ⚡ BERT.
- **Shortlisting** — HR selects finalists; the rest can get constructive rejection emails.
- **Interview Question Generator** — 10 personalized questions per candidate.

### Communication
- **Email Center** — AI‑drafted interview invites, batch send, HR confirmation before anything goes out.
- **Rejection Emails** — constructive, personalized, gentle.
- **Inbox Tracking** — reads candidate replies and classifies intent; auto‑updates offer status.
- **Reminders** — day‑of interview reminders to HR + candidate (scheduled daily at `REMINDER_HOUR`).

### Scheduling
- **Google Calendar integration** — real events, not a mock.
- **Smart Scheduler** — skips weekends, Indian public holidays (2025–26), timezone‑aware (auto‑detects from city), conflict avoidance, business‑hours slots.
- **Auto‑Schedule All** — books every shortlisted candidate in sequence.

### Offers & Negotiation
- **Offer Letters** — FAANG‑grade HTML (Document Agent) or PDF (Onboarding Agent).
- **Offer Tracking** — send → track accepted/declined → branch.
- **Negotiation Advisor** — guidance + draft reply when a candidate pushes back.

### Onboarding
- **Welcome Package** — personalized email + attached documents.
- **Document Checklist** — 8‑item new‑hire checklist with per‑item tracking.
- **Intro Meeting** — auto‑scheduled on the calendar.
- **Company Handbook Generator** — inspiring, structured HTML handbook.

### Intelligence & Ops
- **HR Helpdesk Chatbot** — RAG over `company_faq.txt`.
- **AI Supervisor** — natural‑language control over all tools (LangGraph).
- **Pipeline State Machine** — restart‑safe, 9 stages, history.
- **Live Analytics** — real funnel (uploaded→…→accepted) + score distribution + stats.
- **CSV Export** — the whole candidate pipeline as a spreadsheet.
- **Swappable LLM** — OpenAI / Groq / Ollama / Gemini / OpenRouter via one env var.

---

## 9. How the Key Pieces Actually Work (deep dives)

### 9.1 Hybrid Resume Screening (the standout feature)
Running an LLM on *every* resume is slow and expensive. Our two‑stage approach:

1. **Stage 1 — BERT pre‑filter (free, local):** embed the JD and every resume with `all‑MiniLM‑L6‑v2`, compute cosine similarity, and rank *all* resumes. Zero API cost.
2. **Stage 2 — LLM deep‑eval (top‑K only):** only the top `SCREEN_LLM_TOP_K` (default 5) get a full LLM evaluation (name, skills, projects, reasoning, score). The rest keep their BERT score + regex‑extracted contact info, marked "pre‑screened."

**Result:** on a 14‑resume batch, this is **~5 LLM calls instead of 14 (~64% fewer tokens)** — faster, cheaper, and it still surfaces the best candidates first. Deep‑evaluated candidates always rank above pre‑screened ones.

### 9.2 RAG Helpdesk (grounded answers)
The chatbot never makes up policy. On startup it splits `company_faq.txt` into chunks and embeds each with BERT. For a question, it embeds the query, finds the top‑3 most similar chunks by cosine similarity, and passes *only those* to the LLM with strict instructions to answer **only** from that context (or defer to a human). This is classic **Retrieval‑Augmented Generation**.

### 9.3 Smart Interview Scheduling
Given a candidate and an interviewer city, the scheduler: detects the timezone → scans the next 7 days on Google Calendar → skips weekends and Indian holidays → finds free 1‑hour slots in business hours → books one → sends calendar invites to candidate + HR → sets multi‑stage reminders (1 day, 1 hour, 15 min).

### 9.4 The LangGraph Supervisor (agentic layer)
The dashboard is deterministic (one button = one action). The Supervisor is *agentic*: a single LLM "brain" (via `create_react_agent`) is given 8 tools (wrapping the real agents). It reads a plain‑English request, decides which tool(s) to call, executes them, and can **chain** several in one turn (e.g. "write a JD, then give me interview questions"). The UI shows which tools it used. This realizes the "supervisor + multi‑agent coordination" idea from the original design.

### 9.5 Persistence & State Machine
`store.py` uses stdlib **SQLite** (no ORM, no extra dependency). It stores the whole session as a JSON blob, the current stage, a stage‑history audit trail, and posted jobs. On startup the app restores everything. The stage machine is **forward‑only** so out‑of‑order calls can't rewind visible progress. On restart it even **re‑arms the auto‑relaxation timers** for active jobs.

### 9.6 Swappable LLM Provider
`llm.py` centralizes the model choice. Because Groq, Ollama, Gemini, and OpenRouter all expose an **OpenAI‑compatible API**, switching providers is just a different `base_url` + key — **no code changes, no new dependency**. Set `LLM_PROVIDER` in `.env`. Every agent calls `get_client()` + `MODEL`; the Supervisor calls `get_langchain_llm()`.

### 9.7 Auto JD Relaxation
When a JD is posted, `posting_agent.py` schedules a check (via **APScheduler**) for `RELAXATION_INTERVAL_HOURS` later. If applications are below `APPLICATION_THRESHOLD`, it calls the LLM to *relax* the JD (reduce required years, soften "required" skills, warmer tone) and reposts a new version — then schedules the next check. Fully autonomous.

---

## 10. Full Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Language** | Python 3.12 | Ecosystem for AI + web |
| **Web framework** | FastAPI + Uvicorn | Async, auto‑docs at `/docs`, fast |
| **Frontend** | Vanilla HTML/CSS/JS + Chart.js + jsPDF | No build step, easy to demo |
| **LLM (generation)** | OpenAI‑compatible: **Groq** (default, free), OpenAI, Ollama, Gemini, OpenRouter | Swappable via one env var |
| **Embeddings (BERT)** | `sentence-transformers` `all-MiniLM-L6-v2` | Local, free semantic similarity |
| **Similarity** | scikit‑learn cosine similarity | Screening + RAG |
| **Agent framework** | LangChain + **LangGraph** (`create_react_agent`) | The Supervisor + A2A agent |
| **Observability** | LangSmith (optional, env‑activated) | Trace/debug/eval agent runs |
| **Persistence** | SQLite (stdlib `sqlite3`) | Restart‑safe state, zero deps |
| **Calendar** | Google Calendar API (OAuth2) | Real scheduling |
| **Email (send)** | Gmail SMTP | Invites, offers, rejections |
| **Email (read)** | IMAP (stdlib) | Inbox reply tracking |
| **Email (reminders)** | Gmail API | Day‑of HTML reminders |
| **Messaging** | Telegram Bot API | Job posting |
| **Scheduling jobs** | APScheduler | Auto‑relax + daily reminders |
| **PDF (read)** | PyMuPDF (`fitz`) | Resume text extraction |
| **PDF (write)** | reportlab | Offer letters |
| **Scraping** | BeautifulSoup | Optional JD reference scraping |
| **Deployment** | Docker + docker‑compose | Nasiko A2A packaging |
| **Protocol** | A2A over JSON‑RPC 2.0 | Nasiko agent interface |

---

## 11. Configuration & Tunable Factors

All configured in `hackathon/.env` (copy from `.env.example`). Key knobs:

| Variable | Default | Controls |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Which LLM backend (openai/groq/ollama/gemini/openrouter) |
| `LLM_MODEL` | provider default | Exact model (e.g. `openai/gpt-oss-20b`, `llama-3.3-70b-versatile`) |
| `OPENAI_API_KEY` / `GROQ_API_KEY` | — | Provider credentials |
| `MAX_SHORTLIST` | 5 | Max candidates to shortlist |
| `SCREEN_LLM_TOP_K` | 5 | How many top BERT‑ranked resumes get deep LLM eval |
| `APPLICATION_THRESHOLD` | 5 | Relax the JD if applications fall below this |
| `RELAXATION_INTERVAL_HOURS` | 48 | How often to check + auto‑relax |
| `REMINDER_HOUR` | 8 | Local hour to send day‑of reminders |
| `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` | — | Email send + inbox read |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | — | Job posting |
| `CALENDAR_ID` / `TIMEZONE` / `HR_EMAIL` | primary / Asia/Kolkata / — | Calendar behavior |
| `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` | — | Turn on LangSmith tracing |

**"Factors" that shape outcomes:** the JD style, the exclusion list, the screening top‑K, the shortlist size, the application threshold and relax interval, the business‑hours window and holiday list in the scheduler, and the FAQ content that grounds the helpdesk.

---

## 12. API Reference

The full app exposes ~30 endpoints (interactive docs at `http://localhost:8000/docs`).

**Pipeline & session**
- `GET /api/pipeline` · `POST /api/pipeline/reset` · `GET /api/session` · `GET /api/analytics` · `GET /api/job-status`

**JD & posting**
- `GET /api/jd-styles` · `POST /api/generate-jd` · `POST /api/post-jd` · `POST /api/test-telegram`

**Screening**
- `POST /api/upload-resumes` · `POST /api/screen-resumes` · `POST /api/shortlist` · `POST /api/interview-questions`

**Email**
- `POST /api/draft-emails` · `POST /api/send-emails` · `POST /api/send-rejections`

**Calendar**
- `GET/POST /api/calendar/events` · `DELETE /api/calendar/events/{id}` · `POST /api/calendar/auto-schedule`

**Offers & tracking (Phase 2)**
- `POST /api/offer/send` · `GET /api/offers` · `POST /api/offer/response` · `POST /api/offer/negotiate` · `POST /api/inbox/check` · `POST /api/reminders/send-today`

**Onboarding & documents**
- `POST /api/onboard` · `GET /api/onboarding/checklist` · `POST /api/onboarding/document-received` · `POST /api/onboarding/schedule-intro` · `POST /api/documents/offer-letter` · `POST /api/documents/handbook`

**Helpdesk & Supervisor**
- `POST /api/helpdesk` · `POST /api/agent/chat` (LangGraph Supervisor)

**Export**
- `GET /api/export/candidates.csv`

**A2A agent (Nasiko, port 5000)**
- `POST /` with JSON‑RPC `message/send` → returns a completed Task with the answer as an artifact.

---

## 13. From Idea to Build — The Journey

The project was designed on paper first (see `doc/` — 6 handwritten pages) and built in **5 disciplined phases**:

- **Phase 0 — Hygiene.** Removed ~60% duplicate/junk files, fixed a broken `requirements.txt`, added `.env.example`, corrected docs.
- **Phase 1 — Make it real.** Added SQLite persistence + the 9‑stage state machine so nothing is lost on restart.
- **Phase 2 — Close the loop.** Inbound email tracking, auto reminders, offer→negotiate branch, onboarding checklist + intro meeting, CSV export — with dashboard UI.
- **Phase 3 — Make it agentic.** The LangGraph Supervisor + LangSmith tracing.
- **Phase 4 — Optimize.** Hybrid BERT→LLM screening (~64% fewer tokens) + real analytics.
- **Phase 5 — Ship.** Expanded and modernized the Nasiko A2A agent (9 tools, swappable LLM, LangGraph), verified end‑to‑end.

Every phase was **verified live** (golden‑path runs, a 15‑check smoke test, supervisor tool‑routing, A2A JSON‑RPC calls) and committed to git. See `PROJECT_ANALYSIS_AND_MASTER_PLAN.md` for the full log.

---

## 14. Setup & Running It Yourself

```bash
# 1. Install dependencies
cd hackathon
pip install -r requirements.txt

# 2. Configure secrets
cp .env.example .env
#    → set at minimum an LLM key:
#      free path:  LLM_PROVIDER=groq  + GROQ_API_KEY=...   (console.groq.com)
#      or OpenAI:  LLM_PROVIDER=openai + OPENAI_API_KEY=...
#    → optional: Gmail (send/read), Telegram, Google Calendar (credentials.json)

# 3. (Optional) Google Calendar: place credentials.json in hackathon/,
#    first run opens a browser to log in and creates token.json

# 4. Run
python main.py            # or: python -m uvicorn main:app --port 8000
#    → open http://localhost:8000        (dashboard)
#    → open http://localhost:8000/docs   (all endpoints, "Try it out")

# 5. Smoke test (no external keys needed)
python test_phase2.py
```

**Minimum to demo the AI:** just an LLM key. Gmail/Telegram/Calendar unlock those specific features; without them, actions still record state and advance the pipeline, they just skip the external send.

**Free‑tier note:** Groq limits tokens *per model per day* (~100k). If the Supervisor stops responding, switch `LLM_MODEL` (e.g. between `openai/gpt-oss-20b` and `llama-3.3-70b-versatile`) and restart.

---

## 15. Deployment — With Nasiko and Without

### A) Deploy to Nasiko (the hackathon submission)
The deployable is **`hr-ai-agent/`**.

1. **Test locally first**
   ```bash
   cd hr-ai-agent
   docker build -t hr-ai-agent .
   docker run -p 5000:5000 -e OPENAI_API_KEY=your_key hr-ai-agent
   # or free:  -e LLM_PROVIDER=groq -e GROQ_API_KEY=your_key -e LLM_MODEL=llama-3.3-70b-versatile
   ```
   Then send the JSON‑RPC `message/send` curl from `hr-ai-agent/README.md`.
2. **Deploy** on the Nasiko dashboard → **Add Agent** →
   - **Connect GitHub** (push `hr-ai-agent/` to a repo, select it), **or**
   - **Upload ZIP** of the folder.
3. Nasiko validates (`Dockerfile` + `docker-compose.yml` required), builds the container, reads `AgentCard.json`, and registers the agent. It injects `OPENAI_API_KEY`.

> **This deploy is a manual dashboard action** — it can't be automated from code, but everything it needs is already in the repo and verified.

### B) Deploy the full app without Nasiko
The `hackathon/` app is a normal FastAPI service — host it anywhere:
- **Locally:** `python main.py`.
- **Any VM / container:** `uvicorn main:app --host 0.0.0.0 --port 8000` behind nginx; provide `.env` + `credentials.json` as secrets.
- **PaaS (Render/Railway/Fly/Azure):** set env vars, expose port 8000. (Note: SQLite is a single file — fine for one instance; use a managed DB for multi‑instance.)

---

## 16. Security & Privacy

- **Secrets** live only in `.env`, `credentials.json`, `token.json` — all **gitignored**, never committed.
- **Gmail App Passwords** (not your real password) are used for SMTP/IMAP.
- **Google OAuth** tokens are stored locally in `token.json`.
- **Rotate keys** if they're ever exposed (e.g. pasted into a chat/screenshot): OpenAI, Groq, and the Gmail app password each take ~1 minute to regenerate.
- **Test data caution:** the sample resumes in `data/resumes/` share a placeholder email, and one real CV (`cv siddharth shukla.pdf`) contains a real personal email — remove it if it wasn't yours to publish.
- **Bias:** screening currently sees the whole resume. A future guardrail should strip name/gender/age before scoring (see roadmap).

---

## 17. Known Limitations

- **Single‑user / single active role** at a time (one session). No multi‑recruiter auth yet.
- **SQLite** is single‑file — great for a demo, not for horizontal scaling.
- **APScheduler timers** are in‑memory; jobs are re‑armed on restart, but a very long downtime can miss a window.
- **Free LLM quotas** (Groq per‑model daily cap) can interrupt heavy Supervisor use.
- **Candidate "source"** isn't tracked, so acquisition‑channel analytics aren't available (we show score distribution instead).
- **The Nasiko A2A agent is stateless** — it exposes capabilities as tools but doesn't share the web app's live pipeline state.

---

## 18. What More We Can Do (Roadmap)

**Quality & fairness**
- **Bias‑blind screening** — redact name/gender/age/photo before scoring.
- **Explainable ranking** — side‑by‑side "why A > B".
- **Duplicate/plagiarism detection** across resumes.

**Coverage**
- **Multi‑role / multi‑recruiter** with auth and per‑role pipelines.
- **Multi‑platform posting** (LinkedIn, X, job boards), not just Telegram.
- **Two‑way candidate chatbot** (Telegram) for status + FAQs.
- **Interview scorecard agent** — turn interviewer notes into a structured hire recommendation.

**Intelligence**
- **Audio input** (Whisper) for voice queries — from the original "text + audio {NLP}" idea.
- **Hybrid screening tuning** — learned thresholds, skill‑gap heatmaps.
- **LangSmith evals** — automatic quality scoring of agent responses over time.

**Platform**
- **Managed database** (Postgres) for scale + concurrency.
- **Google Sheets sync** for live shared dashboards.
- **Role‑based access control** and audit logs.
- **Containerize the full app** (not just the A2A agent) for one‑command deploy.

---

## 19. Glossary

- **A2A (Agent‑to‑Agent)** — Nasiko's JSON‑RPC 2.0 protocol for agents to talk to each other and the platform.
- **AgentCard** — the JSON metadata describing an A2A agent (name, version, skills).
- **BERT / embeddings** — turning text into vectors so semantic similarity can be computed locally.
- **RAG (Retrieval‑Augmented Generation)** — fetch relevant context, then let the LLM answer only from it.
- **HITL (Human‑in‑the‑Loop)** — the human approves at key decision points.
- **LangChain / LangGraph** — frameworks for building tool‑calling and multi‑step agents.
- **LangSmith** — observability/tracing for LangChain/LangGraph agents.
- **Supervisor agent** — one LLM that routes a request to the right specialist tools.
- **State machine** — the ordered, forward‑only pipeline stages.
- **Hybrid screening** — cheap BERT ranking for all + expensive LLM eval for the best.
- **JD relaxation** — automatically loosening a job description to attract more applicants.

---

*This guide reflects the project after all 5 build phases. For the technical build log and the original problem analysis, see `PROJECT_ANALYSIS_AND_MASTER_PLAN.md`. For deploying the Nasiko agent, see `hr-ai-agent/README.md`.*
