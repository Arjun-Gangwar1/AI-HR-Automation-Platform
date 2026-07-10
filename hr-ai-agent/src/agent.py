"""
Core agent logic for HR AI Agent — Nasiko A2A deployment.

A LangGraph tool-calling agent (create_react_agent) with 9 specialized HR tools.
The LLM backend is swappable via LLM_PROVIDER (OpenAI by default; free Groq etc.).

The A2A contract is unchanged: Agent().process_message(text) -> str.
"""
from langgraph.prebuilt import create_react_agent

from llm_config import get_langchain_llm, PROVIDER, MODEL
from tools import (
    generate_job_description,
    screen_resume,
    generate_interview_questions,
    generate_offer_letter,
    generate_company_handbook,
    answer_hr_query,
    draft_interview_email,
    negotiation_guidance,
    draft_rejection_email,
)

SYSTEM_PROMPT = """You are an expert HR AI Agent — an intelligent hiring platform that helps \
recruiters and HR teams with the full recruitment lifecycle.

Your capabilities (use the matching tool when asked):
1. JD Generator — compelling, customized Job Descriptions in various styles
2. Resume Screener — evaluate/score a resume against a job description
3. Interview Kit — 10 tailored interview questions with rationales
4. Offer Letter Generator — professional offer letters
5. Company Handbook — comprehensive employee handbooks
6. HR Helpdesk — policy questions (PTO, benefits, remote work, etc.)
7. Email Drafter — interview invitation emails
8. Negotiation Advisor — counter-offer guidance when a candidate pushes back
9. Rejection Email — polite, constructive rejection emails

Be professional, helpful, and proactive. If a request is ambiguous, ask a brief \
clarifying question. Format responses cleanly with headers and bullet points when useful."""


class Agent:
    def __init__(self):
        self.name = "HR AI Agent"

        self.tools = [
            generate_job_description,
            screen_resume,
            generate_interview_questions,
            generate_offer_letter,
            generate_company_handbook,
            answer_hr_query,
            draft_interview_email,
            negotiation_guidance,
            draft_rejection_email,
        ]

        # Provider-swappable LLM (OpenAI default; Groq/Ollama/etc. via LLM_PROVIDER).
        self.llm = get_langchain_llm(temperature=0.2)
        self.agent = create_react_agent(self.llm, self.tools, prompt=SYSTEM_PROMPT)
        print(f"[HR-AI-Agent] LLM provider='{PROVIDER}', model='{MODEL}', tools={len(self.tools)}")

    def process_message(self, message_text: str) -> str:
        """Process one incoming A2A message and return the agent's reply text."""
        result = self.agent.invoke({"messages": [("user", message_text)]})
        messages = result.get("messages", [])
        return messages[-1].content if messages else ""
