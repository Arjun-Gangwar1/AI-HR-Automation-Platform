"""
Helpdesk Agent - RAG-powered HR chatbot for candidate queries
Uses BERT embeddings over company FAQ + Groq LLM for grounded answers
"""
import os
from llm import get_client, MODEL
from utils.bert_utils import get_embedding, compute_similarity
from dotenv import load_dotenv

load_dotenv()
client = get_client()

FAQ_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "company_faq.txt")

_kb_chunks: list[dict] = []


def load_knowledge_base():
    """Load and embed FAQ file into memory."""
    global _kb_chunks
    _kb_chunks = []

    if not os.path.exists(FAQ_FILE):
        print(f"[Helpdesk] FAQ file not found at {FAQ_FILE}. Using empty KB.")
        return

    with open(FAQ_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    raw_chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 30]

    print(f"[Helpdesk] Loading {len(raw_chunks)} FAQ chunks into BERT knowledge base...")
    for chunk in raw_chunks:
        emb = get_embedding(chunk)
        _kb_chunks.append({"text": chunk, "embedding": emb})
    print(f"[Helpdesk] Knowledge base ready with {len(_kb_chunks)} chunks.")


def get_top_context(question: str, top_k: int = 3) -> str:
    """Find top-K most relevant FAQ chunks for the question using BERT similarity."""
    if not _kb_chunks:
        return ""

    q_emb = get_embedding(question)
    scored = []
    for chunk in _kb_chunks:
        score = compute_similarity(q_emb, chunk["embedding"])
        scored.append((score, chunk["text"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [text for _, text in scored[:top_k]]
    return "\n\n---\n\n".join(top_chunks)


# ---------- Company-Grade System Prompt ----------
HELPDESK_SYSTEM_PROMPT = """You are an official HR assistant for our company. You respond exactly like a real, experienced HR representative would in a professional company.

RULES YOU MUST FOLLOW:
1. Answer ONLY based on the provided FAQ context. If the answer is not in the context, say: "I don't have the specific details for that question. Please email hr@company.com or call the HR helpline at ext. 2100 for assistance."
2. Always be warm, professional, and concise — aim for 2-4 sentences max.
3. Never guess, speculate, or make up policies. Accuracy is critical.
4. Use direct, actionable language. Instead of "You may want to check...", say "Here's what the policy states:".
5. When giving policy info, cite specifics: exact numbers of days, percentages, deadlines, names of forms.
6. If someone asks about something sensitive (salary negotiations, termination, disputes), respond with: "For sensitive matters, I recommend scheduling a private meeting with your HR Business Partner. You can reach them at hr@company.com."
7. Format your answers cleanly: use bullet points for lists, bold for emphasis when needed.
8. Always end with a helpful follow-up prompt like "Is there anything else I can help with?" or "Let me know if you need more details on this."

PERSONALITY: You are professional but approachable — imagine a friendly HR manager who genuinely wants to help employees succeed."""


def answer_query(question: str) -> str:
    """Answer a candidate/employee HR query using RAG."""
    context = get_top_context(question, top_k=3)

    if context:
        user_prompt = f"""Company FAQ context:
{context}

Employee/Candidate question: {question}

Respond as per your instructions — use ONLY the context above."""
    else:
        user_prompt = f"""No specific FAQ context is available for this question.

Employee/Candidate question: {question}

Follow your instructions about handling unknown questions."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": HELPDESK_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Sorry, I'm having trouble right now. Please email hr@company.com directly. (Error: {e})"
