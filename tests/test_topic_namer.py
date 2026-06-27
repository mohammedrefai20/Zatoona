"""Tests for auto topic naming. No network: the LLM path is faked or absent."""
import sys
import types

from utils.topic_namer import generate_topic_name


def test_empty_text_returns_default():
    assert generate_topic_name("") == "Untitled notes"
    assert generate_topic_name("   \n ") == "Untitled notes"


def test_fallback_when_llm_unavailable(monkeypatch):
    # Force the LLM import/use to fail -> heuristic fallback (first words).
    monkeypatch.setitem(sys.modules, "langchain_groq", None)  # import returns None -> AttributeError
    title = generate_topic_name("Photosynthesis converts light energy into chemical energy in plants")
    assert title  # never empty
    assert title.lower().startswith("photosynthesis")


def test_happy_path_cleans_llm_title(monkeypatch):
    fake = types.ModuleType("langchain_groq")

    class ChatGroq:
        def __init__(self, **kwargs):
            pass

        def invoke(self, _prompt):
            return types.SimpleNamespace(content='  "Transformer Architecture"\nignored second line')

    fake.ChatGroq = ChatGroq
    monkeypatch.setitem(sys.modules, "langchain_groq", fake)

    title = generate_topic_name("Notes about attention and embeddings in transformers...")
    assert title == "Transformer Architecture"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
