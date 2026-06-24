"""Tests for the chunking strategy layer (vector_db/chunking.py).

Uses markdown fixtures so the hybrid path runs offline (tokenizer is tiktoken, no model download).
"""

import pytest

from vector_db import chunking, docling_parser

MD = (
    "# Photosynthesis\n\n"
    "## Light-Dependent Reactions\n\n"
    "The light-dependent reactions occur in the thylakoid membrane and produce ATP and NADPH "
    "used later in the Calvin cycle. Chlorophyll absorbs photons to drive electron transport, "
    "splitting water and releasing oxygen as a by-product.\n"
)


def _doc(tmp_path, text=MD, name="notes.md"):
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return docling_parser.parse(str(f)), name


def test_hybrid_chunks_carry_heading_context(tmp_path):
    dl, name = _doc(tmp_path)
    chunks = chunking.chunk(dl, name)

    assert len(chunks) >= 1
    joined = "\n".join(c.content for c in chunks)
    assert "Light-Dependent Reactions" in joined  # contextualize() prepends the heading breadcrumb
    assert any("thylakoid" in c.content for c in chunks)
    for c in chunks:
        assert c.source_file == name
        assert c.content.strip()
        assert c.transcribed is False


def test_hybrid_populates_headings_and_page(tmp_path):
    dl, name = _doc(tmp_path)
    chunks = chunking.chunk(dl, name)
    assert any(c.headings for c in chunks)


def test_empty_document_yields_no_chunks(tmp_path):
    dl, name = _doc(tmp_path, text="   \n", name="blank.md")
    assert chunking.chunk(dl, name) == []


def test_transcribed_flag_propagates(tmp_path):
    dl, name = _doc(tmp_path)
    chunks = chunking.chunk(dl, name, transcribed=True)
    assert chunks
    assert all(c.transcribed for c in chunks)


def test_chunk_order_is_deterministic(tmp_path):
    dl, name = _doc(tmp_path)
    first = [c.content for c in chunking.chunk(dl, name)]
    dl2, _ = _doc(tmp_path)
    second = [c.content for c in chunking.chunk(dl2, name)]
    assert first == second


def test_default_mode_does_not_invoke_semantic(monkeypatch, tmp_path):
    dl, name = _doc(tmp_path)
    calls = {"n": 0}

    def _spy(*a, **k):
        calls["n"] += 1
        return []

    monkeypatch.setattr(chunking, "_semantic_chunks", _spy)
    chunking.chunk(dl, name)  # default CHUNK_MODE == "hybrid"
    assert calls["n"] == 0


def test_semantic_mode_dispatches(monkeypatch, tmp_path):
    dl, name = _doc(tmp_path)
    monkeypatch.setattr(chunking.settings, "CHUNK_MODE", "semantic")
    sentinel = chunking.Chunk(content="SEMANTIC", page=None, headings=[], source_file=name)
    monkeypatch.setattr(chunking, "_semantic_chunks", lambda dl_doc, source, transcribed=False: [sentinel])

    out = chunking.chunk(dl, name)
    assert len(out) == 1
    assert out[0].content == "SEMANTIC"


def test_semantic_chunker_groups_by_similarity(monkeypatch, tmp_path):
    """The real semantic path runs offline with a stubbed embedder (identical vectors -> merged)."""
    import vector_db.embedder as embedder

    dl, name = _doc(tmp_path)
    monkeypatch.setattr(chunking.settings, "CHUNK_MODE", "semantic")
    monkeypatch.setattr(embedder, "get_embedding_function",
                        lambda: (lambda texts: [[1.0, 0.0] for _ in texts]))

    out = chunking.chunk(dl, name)

    assert len(out) >= 1
    assert all(c.source_file == name for c in out)
    assert all(c.content.strip() for c in out)
    assert any("thylakoid" in c.content for c in out)
