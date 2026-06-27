"""Auto-name a topic from study material when the user doesn't supply one.

Reuses the Groq model already configured for grading. Always returns a usable
string — if the LLM is unavailable or errors, it falls back to a heuristic so
an upload never fails just because naming did.
"""
from config.settings import GROQ_API_KEY, GROQ_MODEL

_MAX_SAMPLE = 2000


def _fallback(sample: str) -> str:
    words = sample.split()
    title = " ".join(words[:6]).strip(" .,:;-")
    return title[:60] or "Untitled notes"


def generate_topic_name(text: str) -> str:
    sample = (text or "").strip()[:_MAX_SAMPLE]
    if not sample:
        return "Untitled notes"

    try:
        from langchain_groq import ChatGroq

        llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0)
        prompt = (
            "Give a short, specific topic title for the following study notes. "
            "2-5 words, Title Case, no quotes, no trailing punctuation. "
            "Reply with ONLY the title.\n\n"
            f"{sample}"
        )
        raw = llm.invoke(prompt).content
        first_line = (raw or "").strip().splitlines()[0] if (raw or "").strip() else ""
        title = first_line.strip().strip('"').strip("'").strip()[:60]
        return title or _fallback(sample)
    except Exception:
        return _fallback(sample)
