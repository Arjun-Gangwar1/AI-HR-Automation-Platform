# HR AI Agent — Nasiko A2A Deployment

An intelligent HR hiring platform agent that handles the full recruitment lifecycle via the A2A (Agent-to-Agent) protocol.

## 🚀 Skills

| # | Skill | Description |
|---|-------|-------------|
| 1 | **JD Generator** | Generate compelling Job Descriptions in 5 styles |
| 2 | **Resume Screener** | Evaluate resumes against JDs with structured scoring |
| 3 | **Interview Kit** | Generate 10 tailored interview questions |
| 4 | **Offer Letter** | Draft FAANG-grade professional offer letters |
| 5 | **Company Handbook** | Create comprehensive employee handbooks |
| 6 | **HR Helpdesk** | Answer HR policy questions (PTO, benefits, etc.) |
| 7 | **Email Drafter** | Draft interview invitation emails |
| 8 | **Negotiation Advisor** | Counter-offer guidance when a candidate pushes back |
| 9 | **Rejection Email** | Draft polite, constructive rejection emails |

## 📦 Project Structure

```
hr-ai-agent/
├── src/
│   ├── __init__.py
│   ├── __main__.py      # A2A JSON-RPC server (port 5000)
│   ├── models.py        # Pydantic models for A2A protocol
│   ├── agent.py         # LangGraph tool-calling agent (create_react_agent)
│   ├── tools.py         # 9 LangChain @tool functions
│   └── llm_config.py    # Swappable LLM provider (OpenAI / Groq / Ollama / ...)
├── Dockerfile
├── docker-compose.yml
├── AgentCard.json
└── README.md
```

## 🛠️ Local Testing

### Prerequisites
- Docker Desktop installed
- An LLM key: OpenAI (default) **or** a free Groq key (`LLM_PROVIDER=groq`)

### Build & Run (OpenAI)

```bash
cd hr-ai-agent
docker build -t hr-ai-agent .
docker run -p 5000:5000 -e OPENAI_API_KEY=your_key_here hr-ai-agent
```

### Run for free on Groq

```bash
docker run -p 5000:5000 \
  -e LLM_PROVIDER=groq \
  -e LLM_MODEL=llama-3.3-70b-versatile \
  -e GROQ_API_KEY=your_groq_key \
  hr-ai-agent
```

### Test with curl

```bash
curl -X POST http://localhost:5000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Generate a JD for Senior ML Engineer at a fintech startup"}]
      }
    }
  }'
```

## 🚢 Deployment on Nasiko

### Option 1: GitHub
1. Push this folder to a GitHub repo
2. Go to Nasiko Dashboard → Add Agent → Connect GitHub
3. Select your repo — it auto-deploys

### Option 2: ZIP Upload
1. ZIP this folder: `zip -r hr-ai-agent.zip hr-ai-agent/`
2. Go to Nasiko Dashboard → Add Agent → Upload ZIP
3. Upload and wait for deployment

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | — | `openai` (default), `groq`, `ollama`, `gemini`, or `openrouter` |
| `LLM_MODEL` | — | Override the provider's default model |
| `OPENAI_API_KEY` | ✅ if provider=openai | OpenAI key (Nasiko provides this) |
| `GROQ_API_KEY` | ✅ if provider=groq | Free Groq key from console.groq.com |

> The agent defaults to OpenAI (what Nasiko injects). Set `LLM_PROVIDER=groq` to run free.
> Verified locally on Groq `openai/gpt-oss-20b` — the A2A `message/send` call returns a
> completed task with the tool's output.
