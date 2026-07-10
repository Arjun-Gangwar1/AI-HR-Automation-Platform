"""
llm_config.py — self-contained LLM provider switch for the Nasiko A2A agent.

Mirrors the main app's llm.py but stands alone (the deployed agent only ships
its own src/). Pick the backend with LLM_PROVIDER in the environment:

    openai      (default; Nasiko provides OPENAI_API_KEY)
    groq        FREE — set GROQ_API_KEY, LLM_PROVIDER=groq
    ollama      local/offline — run `ollama serve`
    gemini      set GEMINI_API_KEY
    openrouter  set OPENROUTER_API_KEY

Optional LLM_MODEL overrides the provider default.
"""
import os
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()

_CONFIGS = {
    "openai":     {"base_url": None,                                   "key_env": "OPENAI_API_KEY",     "default_model": "gpt-4o"},
    "groq":       {"base_url": "https://api.groq.com/openai/v1",       "key_env": "GROQ_API_KEY",       "default_model": "llama-3.3-70b-versatile"},
    "ollama":     {"base_url": "http://localhost:11434/v1",            "key_env": None,                 "default_model": "llama3.1"},
    "gemini":     {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "key_env": "GEMINI_API_KEY", "default_model": "gemini-1.5-flash"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1",         "key_env": "OPENROUTER_API_KEY", "default_model": "meta-llama/llama-3.3-70b-instruct"},
}


def _cfg() -> dict:
    return _CONFIGS.get(PROVIDER, _CONFIGS["openai"])


def _api_key() -> str:
    cfg = _cfg()
    if cfg["key_env"]:
        return os.getenv(cfg["key_env"], "").strip() or "not-set"
    return "ollama"


MODEL = os.getenv("LLM_MODEL", "").strip() or _cfg()["default_model"]


def get_client() -> OpenAI:
    """Raw OpenAI-SDK client for the selected provider (used by tools.py)."""
    cfg = _cfg()
    kwargs = {"api_key": _api_key()}
    if cfg["base_url"]:
        kwargs["base_url"] = cfg["base_url"]
    return OpenAI(**kwargs)


def get_langchain_llm(temperature: float = 0.2):
    """LangChain chat model for the selected provider (used by agent.py)."""
    from langchain_openai import ChatOpenAI
    cfg = _cfg()
    kwargs = {"model": MODEL, "api_key": _api_key(), "temperature": temperature}
    if cfg["base_url"]:
        kwargs["base_url"] = cfg["base_url"]
    return ChatOpenAI(**kwargs)
