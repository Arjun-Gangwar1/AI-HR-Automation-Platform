"""
llm.py — one place to configure which LLM backend every agent uses.

Why
───
Each agent used to hardcode `OpenAI(api_key=...)` + `model="gpt-4o"`. This
module centralises that so you can switch providers by editing ONE line in
`.env` (`LLM_PROVIDER=...`) with no code changes. All supported providers speak
the OpenAI-compatible chat API, so the existing `openai` SDK works for all of
them — we just change the base URL, key, and default model.

Usage in an agent:
    from llm import get_client, MODEL
    client = get_client()
    client.chat.completions.create(model=MODEL, messages=[...])

Supported LLM_PROVIDER values:
    openai      — OpenAI GPT-4o            (needs OPENAI_API_KEY, paid)
    groq        — Groq (FREE, fast, cloud) (needs GROQ_API_KEY)
    ollama      — local models, offline    (no key; run `ollama serve`)
    gemini      — Google Gemini            (needs GEMINI_API_KEY, free tier)
    openrouter  — OpenRouter               (needs OPENROUTER_API_KEY)

Optional: LLM_MODEL overrides the provider's default model.
(Note: MODEL_NAME in .env is separate — it's only for the optional LangGraph
calendar agent, not this shared client.)
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()

# base_url=None means "use the openai SDK default" (real OpenAI).
_CONFIGS = {
    "openai": {
        "base_url": None,
        "key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "key_env": None,                 # Ollama ignores the key
        "default_model": "llama3.1",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
        "default_model": "gemini-1.5-flash",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
    },
}


def _config() -> dict:
    if PROVIDER not in _CONFIGS:
        print(f"[LLM] Unknown LLM_PROVIDER='{PROVIDER}', falling back to 'openai'.")
        return _CONFIGS["openai"]
    return _CONFIGS[PROVIDER]


def get_client() -> OpenAI:
    """Return an OpenAI-SDK client configured for the selected provider."""
    cfg = _config()
    if cfg["key_env"]:
        api_key = os.getenv(cfg["key_env"], "").strip() or "not-set"
    else:
        api_key = "ollama"  # SDK requires a non-empty string; value is ignored
    kwargs = {"api_key": api_key}
    if cfg["base_url"]:
        kwargs["base_url"] = cfg["base_url"]
    return OpenAI(**kwargs)


# The model name every agent passes to chat.completions.create(model=MODEL).
MODEL = os.getenv("LLM_MODEL", "").strip() or _config()["default_model"]

print(f"[LLM] Provider='{PROVIDER}', model='{MODEL}'.")
