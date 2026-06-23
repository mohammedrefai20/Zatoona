import fitz
import pytest

from vector_db.ingestion import chunk_pdf


def _make_pdf(path, text):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_chunk_pdf_produces_tagged_chunks(tmp_path):
    pdf = tmp_path / "notes.pdf"
    _make_pdf(
        pdf,
        "Photosynthesis\n\n"
        "Plants convert light energy into chemical energy.\n"
        "Chlorophyll in the chloroplasts absorbs sunlight.",
    )

    records = chunk_pdf(str(pdf), topic="biology", session_id="s1")

    assert len(records) >= 1
    for r in records:
        assert r.topic == "biology"
        assert r.session_id == "s1"
        assert r.source_file == "notes.pdf"
        assert isinstance(r.page, int)
        assert r.content.strip()
        assert r.chunk_id.startswith("s1:notes.pdf:")
    assert len({r.chunk_id for r in records}) == len(records)


def test_multipage_pdf_has_unique_ids(tmp_path):
    pdf = tmp_path / "multi.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Subject {i}\n\nNotes about subject number {i} for studying.")
    doc.save(str(pdf))
    doc.close()

    records = chunk_pdf(str(pdf), topic="t", session_id="s1")

    assert len(records) >= 3
    assert len({r.chunk_id for r in records}) == len(records)
    assert max(r.page for r in records) >= 2


def test_min_chunk_chars_filters_short_pieces(tmp_path, monkeypatch):
    from vector_db import ingestion

    monkeypatch.setattr(ingestion.settings, "MIN_CHUNK_CHARS", 100000)
    pdf = tmp_path / "notes.pdf"
    _make_pdf(pdf, "Photosynthesis\n\nPlants convert light energy into chemical energy.")

    assert chunk_pdf(str(pdf), topic="t", session_id="s1") == []


def test_empty_pdf_yields_no_chunks(tmp_path):
    pdf = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf))
    doc.close()

    assert chunk_pdf(str(pdf), topic="x", session_id="s1") == []


def test_unsupported_file_raises(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("hello")
    with pytest.raises(ValueError):
        chunk_pdf(str(bad), topic="x", session_id="s1")


def test_missing_file_raises():
    with pytest.raises(ValueError):
        chunk_pdf("does_not_exist.pdf", topic="x", session_id="s1")


def test_unknown_embedding_provider_raises(monkeypatch):
    from vector_db import embedder

    embedder._cached_ef = None
    monkeypatch.setattr(embedder.settings, "EMBEDDING_PROVIDER", "groq")
    with pytest.raises(RuntimeError):
        embedder.get_embedding_function()


def test_openai_provider_without_key_raises(monkeypatch):
    from vector_db import embedder

    embedder._cached_ef = None
    monkeypatch.setattr(embedder.settings, "EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr(embedder.settings, "OPENAI_API_KEY", "")
    with pytest.raises(RuntimeError):
        embedder.get_embedding_function()


def test_auto_provider_without_key_uses_local(monkeypatch):
    from vector_db import embedder

    embedder._cached_ef = None
    monkeypatch.setattr(embedder.settings, "EMBEDDING_PROVIDER", "auto")
    monkeypatch.setattr(embedder.settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(embedder, "_local_ef", lambda: "LOCAL_EF")
    assert embedder.get_embedding_function() == "LOCAL_EF"
    embedder._cached_ef = None
