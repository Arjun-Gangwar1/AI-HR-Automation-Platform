
# 🚀 AI HR Automation Platform

> AI-powered HR automation system with LLM-based resume screening, job posting, and email automation.

## 👨‍💻 My Contribution
- Integrated LLM-based resume screening
- Built automation pipeline for HR workflows
- Improved system performance and structure

A comprehensive HR automation system with integrated Google Calendar scheduling capabilities.
Team - Ozark


## 🧠 Tech Stack
- Python 3.12
- FastAPI (web server + REST API)
- OpenAI GPT-4o (all generative agents: JD, screening, email, interview, documents, helpdesk)
- sentence-transformers `all-MiniLM-L6-v2` (BERT embeddings for helpdesk RAG)
- Google Calendar API (OAuth2) — interview scheduling
- Gmail SMTP — email sending
- Telegram Bot API + APScheduler — job posting & auto-relax
- reportlab — PDF offer letters

> Note: an earlier draft mentioned Groq/Ollama, but the current code uses **OpenAI GPT-4o** everywhere.
> See `PROJECT_ANALYSIS_AND_MASTER_PLAN.md` for full status and the build roadmap.

## 📸 Demo
(Add screenshots here)

## Features

### Core HR Functions
- **Job Description Generator** - AI-powered JD creation
- **Job Posting** - Multi-platform job posting (Telegram, etc.)
- **Resume Screening** - Automated candidate screening with ML
- **Email Agent** - Draft and send interview emails
- **Interview Scheduler** - Smart calendar-based scheduling
- **Helpdesk** - Knowledge base Q&A system
- **Onboarding** - Automated onboarding workflows
- **Interview Questions** - Generate role-specific questions

### Calendar Integration
- **Google Calendar Sync** - Real-time calendar integration
- **Smart Scheduling** - Automatic slot finding with:
  - Weekend detection
  - Holiday awareness (Indian holidays pre-configured)
  - Conflict avoidance
  - Timezone support (auto-detects from city)
- **Automated Invites** - Email invitations to candidates and HR
- **Reminder Service** - Day-of email reminders
- **Full CRUD** - Create, read, update, delete calendar events

## Project Structure

```
hackathon/
├── agents/                      # AI agent modules
│   ├── calendar_agent.py       # Google Calendar integration (NEW)
│   ├── email_agent.py          # Email drafting and sending
│   ├── helpdesk_agent.py       # FAQ/knowledge base
│   ├── interview_agent.py      # Interview question generation
│   ├── jd_agent.py            # Job description generation
│   ├── onboarding_agent.py    # Onboarding automation
│   ├── posting_agent.py       # Job posting
│   └── screening_agent.py     # Resume screening
│
├── calendar_service/           # Google Calendar service (NEW)
│   ├── __init__.py            # Module exports
│   ├── auth.py                # Google OAuth authentication
│   ├── calendar_tools.py      # Calendar CRUD operations
│   ├── smart_scheduler.py     # Intelligent slot finding
│   ├── reminder_service.py    # Email reminders
│   ├── graph.py               # LangGraph agent (optional)
│   └── diagnose.py            # Calendar setup diagnostics
│
├── data/                       # Data files
│   ├── resumes/               # Candidate resumes
│   ├── onboarding_docs/       # Onboarding materials
│   └── company_faq.txt        # Helpdesk knowledge base
│
├── static/                     # Frontend files
│   ├── index.html             # Main dashboard
│   ├── app.js                 # Frontend logic
│   └── style.css              # Styling
│
├── utils/                      # Utility modules
│   ├── bert_utils.py          # ML utilities
│   └── pdf_utils.py           # PDF processing
│
├── main.py                     # FastAPI server
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
└── credentials.json            # Google OAuth credentials
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `hackathon/.env.example` to `hackathon/.env` and fill in real values. Key variables:

```env
# API Keys
OPENAI_API_KEY=your_openai_api_key_here

# Google Calendar Settings
CREDENTIALS_FILE=credentials.json
TOKEN_FILE=token.json
CALENDAR_ID=primary
TIMEZONE=Asia/Kolkata
HR_EMAIL=your_gmail@gmail.com

# LLM Settings (for calendar agent)
MODEL_NAME=gpt-4o
MAX_TOKENS=4096

# Telegram (optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Setup Google Calendar API

#### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable **Google Calendar API**

#### Step 2: Create OAuth Credentials
1. Navigate to **Credentials** → **+ CREATE CREDENTIALS**
2. Select **OAuth client ID**
3. Application type: **Desktop app**
4. Click **CREATE**
5. **Download JSON** file
6. Rename to `credentials.json` and place in project root

#### Step 3: First-time Authentication
```bash
# Run diagnostics to verify setup
python -m calendar_service.diagnose

# Start the server (will open browser for Google login on first run)
python main.py
```

The browser will open for Google login. After authorization:
- `token.json` will be created automatically
- Subsequent runs won't require browser login

### 4. Verify Calendar Setup

```bash
# Run the diagnostic tool
python -m calendar_service.diagnose
```

This will check:
- ✅ .env configuration
- ✅ credentials.json presence
- ✅ Google Calendar API connection
- ✅ Available calendars
- ✅ Existing events
- ✅ Timezone settings

## Running the Application

### Start the Server

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Access the dashboard at: `http://localhost:8000`

## API Endpoints

### Calendar Endpoints

- `GET /api/calendar/events` - Get all upcoming events
- `GET /api/calendar/events/{year}/{month}` - Get events for specific month
- `POST /api/calendar/events` - Create new calendar event
- `DELETE /api/calendar/events/{event_id}` - Delete event

### Other Endpoints

- `POST /api/jd/generate` - Generate job description
- `POST /api/posting/post` - Post job opening
- `POST /api/screening/screen` - Screen resumes
- `POST /api/email/draft` - Draft interview emails
- `POST /api/email/send` - Send emails
- `POST /api/helpdesk/query` - Ask helpdesk question
- `POST /api/onboarding/send` - Send onboarding package
- `POST /api/interview/questions` - Generate interview questions

### Pipeline State (Phase 1 — SQLite-backed)

- `GET  /api/pipeline` - Current pipeline stage + full stage list + history
- `POST /api/pipeline/reset` - Clear the session and start a fresh role

### Phase 2 — Tracking, reminders, offers, onboarding

- `POST /api/inbox/check` - Scan HR inbox (IMAP), classify candidate replies (confirmed/declined/reschedule/question), auto-update offer status
- `POST /api/reminders/send-today` - Manually send day-of interview reminders (also runs daily at `REMINDER_HOUR`)
- `POST /api/offer/send` - Generate + email an offer letter and start tracking it
- `GET  /api/offers` - List all tracked offers + responses
- `POST /api/offer/response` - Record accepted / declined
- `POST /api/offer/negotiate` - Get HR negotiation guidance when a candidate pushes back
- `GET  /api/onboarding/checklist?candidate_id=` - New-hire document checklist + status
- `POST /api/onboarding/document-received` - Mark a document received
- `POST /api/onboarding/schedule-intro` - Schedule the intro / orientation meeting
- `GET  /api/export/candidates.csv` - Export the pipeline (candidates + statuses) as CSV

## Calendar Features

### Smart Interview Scheduling

The calendar agent automatically:

1. **Finds Available Slots**
   - Searches next 7 days (configurable)
   - Skips weekends (Sat/Sun)
   - Avoids Indian holidays (2025-2026 pre-configured)
   - Checks for conflicts with existing events
   - Suggests 10 AM - 4 PM slots (local time)

2. **Timezone Intelligence**
   - Auto-detects timezone from city name
   - Supports major cities worldwide
   - Shows times in interviewer's local timezone
   - Handles IST, EST, PST, GMT, etc.

3. **Automated Booking**
   - Creates Google Calendar event
   - Sends email invites to candidate + HR
   - Sets up reminders:
     - 1 day before (email)
     - 1 hour before (email)
     - 15 minutes before (popup)

### Example: Schedule Interview

```python
from agents.calendar_agent import schedule_interview

result = schedule_interview(
    candidate={"name": "John Doe", "email": "john@example.com"},
    datetime_str="",  # Empty = auto-find slot
    role="Senior Software Engineer",
    duration_minutes=60,
    meeting_link="https://meet.google.com/abc-def-ghi"
)

# Result:
# {
#   "status": "created",
#   "event_id": "abc12345",
#   "event_link": "https://calendar.google.com/...",
#   "message": "Interview scheduled for John Doe on Monday, 10 March 2026 at 10:00 AM IST"
# }
```

## Calendar Service Modules

### `auth.py`
- Google OAuth2 authentication
- Token management
- Auto-refresh expired tokens

### `calendar_tools.py`
- 10 calendar tools (LangChain compatible)
- CRUD operations for events
- Search and list functionality
- Day-of reminder integration

### `smart_scheduler.py`
- Intelligent slot finding
- Holiday and weekend detection
- Timezone conversion
- Conflict avoidance

### `reminder_service.py`
- Day-of email reminders
- Beautiful HTML email templates
- Gmail API integration
- Can be scheduled with cron/Task Scheduler

### `graph.py` (Optional)
- LangGraph-based conversational agent
- Multi-turn interview scheduling
- Tool calling with OpenAI
- Can be used standalone or integrated

## Troubleshooting

### "No events showing in calendar"
1. Run: `python -m calendar_service.diagnose`
2. Check if `CALENDAR_ID` is correct
3. Verify events exist in the correct Google account
4. Ensure timezone settings match

### "Authentication failed"
1. Delete `token.json`
2. Re-run the application
3. Complete browser authentication again

### "ImportError: No module named calendar_service"
1. Make sure you're in the `hackathon` directory
2. Check that `calendar_service/__init__.py` exists
3. Install dependencies: `pip install -r requirements.txt`

### "Calendar API not enabled"
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable **Google Calendar API** for your project

## Migration from Mock Calendar

The old in-memory mock calendar has been completely replaced with real Google Calendar integration. Key changes:

**Before (Mock):**
- Events stored in memory (lost on restart)
- No external integration
- Simple CRUD only

**After (Real Calendar):**
- Events synced with Google Calendar
- Persistent storage
- Smart scheduling with conflict detection
- Email invitations and reminders
- Timezone support
- Holiday awareness

All existing API endpoints remain the same - the integration is seamless!

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI GPT-4o key — used by all generative agents |
| `CREDENTIALS_FILE` | Yes | `credentials.json` | Google OAuth credentials |
| `TOKEN_FILE` | No | `token.json` | OAuth token storage |
| `CALENDAR_ID` | No | `primary` | Google Calendar ID to use |
| `TIMEZONE` | No | `Asia/Kolkata` | Default timezone |
| `HR_EMAIL` | Yes | - | HR's Gmail address |
| `MODEL_NAME` | No | `gpt-4o` | OpenAI model for calendar agent |
| `MAX_TOKENS` | No | `4096` | Max tokens for LLM responses |

`MODEL_NAME` / `MAX_TOKENS` are only used by the optional LangGraph conversational calendar agent (`calendar_service/graph.py`).

## Contributing

To add new calendar features:

1. Add tool functions to `calendar_service/calendar_tools.py`
2. Update `calendar_service/__init__.py` exports
3. Use tools in `agents/calendar_agent.py`
4. Add API endpoints in `main.py` if needed

## Support

For issues related to:
- **Calendar Integration**: Check `calendar_service/diagnose.py` output
- **API Errors**: Review FastAPI logs in terminal
- **Google OAuth**: Ensure credentials.json is valid
- **Dependencies**: Run `pip install -r requirements.txt --upgrade`

## License

This project is provided as-is for hackathon/educational purposes.
