import pytest
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from vector_db import chroma_client, ingestion, notion


def _rt(text):
    return {"rich_text": [{"plain_text": text}]}


NOTION_PAGE = {
    "title": "Cell Biology",
    "url": "https://notion.so/Cell-Biology-abc123",
    "blocks": [
        {"type": "heading_1", "heading_1": _rt("Cell Biology")},
        {"type": "paragraph", "paragraph": _rt("The cell is the basic unit of life.")},
        {"type": "heading_2", "heading_2": _rt("Mitochondria")},
        {
            "type": "paragraph",
            "paragraph": _rt("Mitochondria are the powerhouse of the cell and make ATP through respiration."),
            "children": [
                {"type": "bulleted_list_item",
                 "bulleted_list_item": _rt("The inner membrane hosts the electron transport chain.")},
            ],
        },
        {"type": "callout", "callout": _rt("ATP is the energy currency of the cell.")},
        {"type": "image", "image": {"file": {"url": "https://example.com/diagram.png"}}},
        {"type": "child_database", "child_database": {"title": "Glossary"}},
    ],
}

IMAGE_ONLY_PAGE = {
    "title": "Diagram dump",
    "id": "page-2",
    "blocks": [
        {"type": "image", "image": {"file": {"url": "https://example.com/a.png"}}},
        {"type": "embed", "embed": {"url": "https://youtu.be/x"}},
    ],
}


class FakeCollection:
    def __init__(self):
        self.added = None

    def upsert(self, ids, documents, metadatas):
        self.added = (ids, documents, metadatas)


class FakeEF(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return [[0.0, 0.0, 0.0, 0.0] for _ in input]

    @staticmethod
    def name() -> str:
        return "fake"


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(chroma_client.settings, "CHROMA_PERSIST_DIR", str(tmp_path))
    monkeypatch.setattr(chroma_client, "get_embedding_function", lambda: FakeEF())
    chroma_client._clients.clear()
    yield tmp_path
    chroma_client._clients.clear()


# --- T007: notion.normalize_page ---------------------------------------------

def test_normalize_page_extracts_readable_blocks_with_structure():
    text, ref, title = notion.normalize_page(NOTION_PAGE)

    assert title == "Cell Biology"
    assert ref == "https://notion.so/Cell-Biology-abc123"
    assert "Mitochondria" in text
    assert "powerhouse of the cell" in text
    assert "electron transport chain" in text  # nested child block captured
    assert "ATP is the energy currency" in text


def test_normalize_page_skips_images_embeds_and_databases():
    text, _, _ = notion.normalize_page(NOTION_PAGE)
    assert "diagram.png" not in text
    assert "Glossary" not in text  # child_database skipped


def test_normalize_page_with_no_readable_text_is_empty():
    text, ref, title = notion.normalize_page(IMAGE_ONLY_PAGE)
    assert text.strip() == ""
    assert ref == "page-2"
    assert title == "Diagram dump"


# --- T008: ingest_text -------------------------------------------------------

def test_ingest_text_stores_notion_provenance():
    text, ref, title = notion.normalize_page(NOTION_PAGE)
    coll = FakeCollection()

    n = ingestion.ingest_text(text, ref, topic="biology", session_id="s1",
                              source_type="notion", title=title, collection=coll)

    assert n >= 1
    ids, _, metas = coll.added
    assert len(ids) == n
    assert all(m["source_type"] == "notion" for m in metas)
    assert all(m["source_ref"] == ref for m in metas)
    assert all(m["notion_page"] == "Cell Biology" for m in metas)
    assert all(m["topic"] == "biology" for m in metas)
    assert all(m["session_id"] == "s1" for m in metas)


def test_ingest_text_empty_stores_nothing():
    coll = FakeCollection()
    n = ingestion.ingest_text("   \n  ", "ref", topic="t", session_id="s1",
                              source_type="notion", title="Blank", collection=coll)
    assert n == 0
    assert coll.added is None


def test_ingest_text_is_session_scoped_and_retrievable(isolated):
    from vector_db import retriever

    text, ref, title = notion.normalize_page(NOTION_PAGE)
    s1 = chroma_client.get_collection("s1")
    n = ingestion.ingest_text(text, ref, topic="biology", session_id="s1",
                              source_type="notion", title=title, collection=s1)

    assert n >= 1
    assert s1.count() == n
    assert chroma_client.get_collection("s2").count() == 0

    chunks = retriever.search("mitochondria", session_id="s1", collection=s1, mode="dense")
    assert len(chunks) >= 1
    assert all(set(c.model_dump()) == {"chunk_id", "topic", "content", "session_id"} for c in chunks)


# --- T013: ingest_url (single video) -----------------------------------------

def test_ingest_url_video_stores_youtube_provenance(monkeypatch):
    from vector_db import loaders, youtube

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    monkeypatch.setattr(youtube, "fetch_transcript", lambda vid: [
        loaders.TextUnit(text="intro to cellular respiration and atp", source_file=vid,
                         timestamp=0.0, transcribed=True),
        loaders.TextUnit(text="the electron transport chain releases energy", source_file=vid,
                         timestamp=12.0, transcribed=True),
    ])
    coll = FakeCollection()

    n = ingestion.ingest_url(url, topic="biology", session_id="s1", collection=coll)

    assert n >= 1
    ids, _, metas = coll.added
    assert len(ids) == n
    assert all(m["source_type"] == "youtube" for m in metas)
    assert all(m["source_ref"] == url for m in metas)
    assert all("timestamp" in m for m in metas)


def test_ingest_url_video_no_captions_fallback_off_returns_zero(monkeypatch):
    from vector_db import youtube

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    monkeypatch.setattr(youtube, "fetch_transcript", lambda vid: [])
    monkeypatch.setattr(ingestion.settings, "YOUTUBE_ASR_FALLBACK", False)
    coll = FakeCollection()

    n = ingestion.ingest_url(url, topic="biology", session_id="s1", collection=coll)

    assert n == 0
    assert coll.added is None


# --- T018: ingest_url (playlist) ---------------------------------------------

def test_ingest_url_playlist_reports_per_item_outcomes(monkeypatch):
    from vector_db import loaders, youtube

    monkeypatch.setattr(youtube, "list_playlist", lambda url: ["good1", "bad", "good2"])
    monkeypatch.setattr(ingestion.settings, "YOUTUBE_ASR_FALLBACK", False)

    def fake_fetch(vid):
        if vid == "bad":
            raise ValueError("video is private")
        return [loaders.TextUnit(text=f"lecture {vid} on cellular respiration and atp",
                                 source_file=vid, timestamp=0.0, transcribed=True)]
    monkeypatch.setattr(youtube, "fetch_transcript", fake_fetch)

    outcomes = ingestion.ingest_url("https://www.youtube.com/playlist?list=PL123",
                                    topic="biology", session_id="s1", collection=FakeCollection())

    ingested = [o for o in outcomes if o["status"] == "ingested"]
    skipped = [o for o in outcomes if o["status"] == "skipped"]
    assert len(ingested) == 2
    assert all(o["stored_count"] >= 1 for o in ingested)
    assert len(skipped) == 1
    assert "private" in skipped[0]["reason"]


def test_ingest_url_playlist_reports_cap(monkeypatch):
    from vector_db import loaders, youtube

    monkeypatch.setattr(youtube.settings, "YOUTUBE_PLAYLIST_MAX", 2)
    monkeypatch.setattr(youtube, "list_playlist", lambda url: ["a", "b"])  # already capped
    monkeypatch.setattr(youtube, "fetch_transcript",
                        lambda vid: [loaders.TextUnit(text="cells and energy and atp",
                                                      source_file=vid, timestamp=0.0)])

    outcomes = ingestion.ingest_url("https://www.youtube.com/playlist?list=PL123",
                                    topic="biology", session_id="s1", collection=FakeCollection())

    assert any(o["status"] == "capped" and "capped" in o["reason"] for o in outcomes)
