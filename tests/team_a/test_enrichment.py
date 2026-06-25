import pytest
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from config import settings
from vector_db import chroma_client, enrichment


def _match(meta, where):
    return all(meta.get(k) == v for k, v in (where or {}).items())


class FakeCollection:
    """In-memory stand-in for a Chroma collection (upsert/get/delete/count by metadata)."""

    def __init__(self):
        self.records = {}

    def upsert(self, ids, documents, metadatas):
        for i, d, m in zip(ids, documents, metadatas):
            self.records[i] = (d, m)

    def get(self, where=None, include=None):
        ids, docs, metas = [], [], []
        for i, (d, m) in self.records.items():
            if _match(m, where):
                ids.append(i)
                docs.append(d)
                metas.append(m)
        return {"ids": ids, "documents": docs, "metadatas": metas}

    def delete(self, where=None):
        doomed = [i for i, (d, m) in self.records.items() if _match(m, where)]
        for i in doomed:
            del self.records[i]

    def count(self):
        return len(self.records)


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


def _seed_own(coll, session_id="s1", topic="biology"):
    coll.upsert(["s1:notes.md:0:0"], ["the cell is the basic unit of life"],
                [{"topic": topic, "session_id": session_id, "source_type": "file",
                  "source_file": "notes.md"}])


# --- T006 / T007: default-off guarantee --------------------------------------

def test_propose_disabled_returns_empty_and_never_searches(monkeypatch):
    calls = []
    monkeypatch.setattr(enrichment, "search_web", lambda *a, **k: calls.append("search") or [])
    coll = FakeCollection()
    _seed_own(coll)

    assert enrichment.propose("s1", enabled=False, collection=coll) == []
    assert calls == []          # no web search attempted
    assert coll.count() == 1    # nothing stored


def test_ingest_approved_disabled_stores_nothing(monkeypatch):
    fetched = []
    monkeypatch.setattr(enrichment, "fetch_clean", lambda url: fetched.append(url) or ("text", "Title"))
    coll = FakeCollection()
    proposals = [enrichment.Proposal(title="T", url="http://x", snippet="s", topic="biology")]

    assert enrichment.ingest_approved(proposals, "s1", enabled=False, collection=coll) == []
    assert fetched == []        # no page fetched
    assert coll.count() == 0


def test_enrichment_defaults_off():
    assert settings.ENRICH_ENABLED is False


def test_enablement_is_a_runtime_arg_not_a_sticky_setting(monkeypatch):
    # Even if the baseline setting were flipped on, the explicit per-call arg governs.
    monkeypatch.setattr(enrichment.settings, "ENRICH_ENABLED", True)
    assert enrichment.propose("s1", enabled=False, collection=FakeCollection()) == []


# --- T009: derive_queries + search_web ---------------------------------------

def test_derive_queries_returns_distinct_topics():
    coll = FakeCollection()
    coll.upsert(
        ["s1:n:0:0", "s1:n:0:1", "s1:m:0:0"],
        ["a", "b", "c"],
        [{"topic": "biology", "session_id": "s1", "source_type": "file"},
         {"topic": "biology", "session_id": "s1", "source_type": "file"},
         {"topic": "physics", "session_id": "s1", "source_type": "file"}],
    )
    assert enrichment.derive_queries("s1", collection=coll) == ["biology", "physics"]


def test_derive_queries_empty_collection_returns_empty():
    assert enrichment.derive_queries("s1", collection=FakeCollection()) == []


def test_derive_queries_ignores_existing_web_chunks():
    coll = FakeCollection()
    coll.upsert(
        ["s1:n:0:0", "s1:w:0:0"], ["a", "b"],
        [{"topic": "biology", "session_id": "s1", "source_type": "file"},
         {"topic": "from-web", "session_id": "s1", "source_type": "web"}],
    )
    assert enrichment.derive_queries("s1", collection=coll) == ["biology"]


def test_search_web_dedupes_and_drops_already_stored(monkeypatch):
    results = {
        "biology": [
            {"title": "Cell", "href": "http://a", "body": "about cells"},
            {"title": "Dup", "href": "http://a", "body": "dup url"},
            {"title": "Mito", "href": "http://b", "body": "mitochondria"},
        ],
        "physics": [
            {"title": "Force", "href": "http://c", "body": "forces"},
            {"title": "Known", "href": "http://known", "body": "already stored"},
        ],
    }
    monkeypatch.setattr(enrichment, "_ddgs_search", lambda q, n: results.get(q, []))

    props = enrichment.search_web(["biology", "physics"], existing_refs={"http://known"})

    assert [p.url for p in props] == ["http://a", "http://b", "http://c"]
    assert props[0].topic == "biology"
    assert props[2].topic == "physics"


# --- T010: fetch_clean + propose (no storage) --------------------------------

def test_fetch_clean_extracts_text_and_title(monkeypatch):
    import trafilatura
    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: "<html>raw</html>")
    monkeypatch.setattr(trafilatura, "extract", lambda html, **k: "clean main content about cells")

    result = enrichment.fetch_clean("http://x")
    assert result is not None
    text, title = result
    assert text == "clean main content about cells"
    assert isinstance(title, str) and title


def test_fetch_clean_none_when_no_main_text(monkeypatch):
    import trafilatura
    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: "<html></html>")
    monkeypatch.setattr(trafilatura, "extract", lambda html, **k: None)
    assert enrichment.fetch_clean("http://x") is None


def test_fetch_clean_none_when_unfetchable(monkeypatch):
    import trafilatura
    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: None)
    assert enrichment.fetch_clean("http://x") is None


def test_propose_enabled_caps_and_stores_nothing(monkeypatch):
    monkeypatch.setattr(enrichment.settings, "ENRICH_MAX_DOCS", 2)
    coll = FakeCollection()
    _seed_own(coll)
    many = [{"title": f"R{i}", "href": f"http://{i}", "body": "b"} for i in range(5)]
    monkeypatch.setattr(enrichment, "_ddgs_search", lambda q, n: many)

    props = enrichment.propose("s1", enabled=True, collection=coll)

    assert len(props) <= 2
    assert coll.count() == 1  # propose writes nothing


# --- T011: ingest_approved stores only approved as source_type="web" ---------

def test_ingest_approved_stores_only_approved_as_web(monkeypatch):
    monkeypatch.setattr(
        enrichment, "fetch_clean",
        lambda url: ("Mitochondria are the powerhouse of the cell and produce ATP.", "Cell Page"),
    )
    coll = FakeCollection()
    approved = [enrichment.Proposal(title="Cell Page", url="http://a", snippet="s", topic="biology")]

    outcomes = enrichment.ingest_approved(approved, "s1", enabled=True, collection=coll)

    assert all(o["status"] == "ingested" for o in outcomes)
    data = coll.get(where={"source_type": "web"})
    assert len(data["ids"]) >= 1
    assert all(m["source_type"] == "web" for m in data["metadatas"])
    assert all(m["source_ref"] == "http://a" for m in data["metadatas"])
    # a URL that was never approved is never stored
    assert all(m["source_ref"] != "http://rejected" for m in data["metadatas"])


def test_ingest_approved_web_is_session_scoped_and_retrievable(isolated, monkeypatch):
    from vector_db import retriever

    monkeypatch.setattr(
        enrichment, "fetch_clean",
        lambda url: ("Photosynthesis converts light energy into chemical energy in plants.", "Photo"),
    )
    s1 = chroma_client.get_collection("s1")
    approved = [enrichment.Proposal(title="Photo", url="http://p", snippet="s", topic="biology")]

    outcomes = enrichment.ingest_approved(approved, "s1", enabled=True, collection=s1)

    assert any(o["status"] == "ingested" for o in outcomes)
    assert s1.count() >= 1
    assert chroma_client.get_collection("s2").count() == 0

    chunks = retriever.search("photosynthesis", session_id="s1", collection=s1, mode="dense")
    assert len(chunks) >= 1
    assert all(set(c.model_dump()) == {"chunk_id", "topic", "content", "session_id"} for c in chunks)


# --- T015: list + bound ------------------------------------------------------

def test_list_enrichment_returns_only_web_items():
    coll = FakeCollection()
    coll.upsert(
        ["s1:n:0:0", "s1:w:0:0"], ["own notes", "web page text"],
        [{"topic": "bio", "session_id": "s1", "source_type": "file", "source_file": "n"},
         {"topic": "bio", "session_id": "s1", "source_type": "web",
          "source_ref": "http://a", "notion_page": "Web Title"}],
    )
    items = enrichment.list_enrichment("s1", collection=coll)

    assert len(items) == 1
    assert items[0]["url"] == "http://a"
    assert items[0]["title"] == "Web Title"


def test_ingest_approved_enforces_max_docs_cap(monkeypatch):
    monkeypatch.setattr(enrichment.settings, "ENRICH_MAX_DOCS", 3)
    monkeypatch.setattr(enrichment, "fetch_clean",
                        lambda url: ("Clean readable content about the subject and its details.", "T"))
    coll = FakeCollection()
    approved = [enrichment.Proposal(title=f"T{i}", url=f"http://{i}", snippet="s", topic="biology")
                for i in range(5)]

    outcomes = enrichment.ingest_approved(approved, "s1", enabled=True, collection=coll)

    ingested = [o for o in outcomes if o["status"] == "ingested"]
    capped = [o for o in outcomes if o["status"] == "skipped" and "cap" in o["reason"]]
    assert len(ingested) == 3
    assert len(capped) == 2


# --- T016: removal + isolation -----------------------------------------------

def test_remove_enrichment_deletes_only_web_and_leaves_own_material():
    coll = FakeCollection()
    coll.upsert(
        ["s1:n:0:0", "s1:y:0:0", "s1:w:0:0", "s1:w:0:1"],
        ["file", "youtube", "web1", "web2"],
        [{"topic": "bio", "session_id": "s1", "source_type": "file"},
         {"topic": "bio", "session_id": "s1", "source_type": "youtube"},
         {"topic": "bio", "session_id": "s1", "source_type": "web", "source_ref": "http://a"},
         {"topic": "bio", "session_id": "s1", "source_type": "web", "source_ref": "http://b"}],
    )

    removed = enrichment.remove_enrichment("s1", collection=coll)

    assert removed == 2
    remaining = {m["source_type"] for _, (d, m) in coll.records.items()}
    assert remaining == {"file", "youtube"}
    assert coll.count() == 2
