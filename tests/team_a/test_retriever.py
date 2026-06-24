from vector_db import retriever


class FakeDenseCollection:
    def __init__(self, ids, docs, metas):
        self._ids, self._docs, self._metas = ids, docs, metas
        self.last_where = "unset"

    def count(self):
        return len(self._ids)

    def query(self, query_texts, n_results, where=None):
        self.last_where = where
        return {
            "ids": [self._ids[:n_results]],
            "documents": [self._docs[:n_results]],
            "metadatas": [self._metas[:n_results]],
        }


class FakeHybridCollection(FakeDenseCollection):
    def get(self, where=None, include=None):
        return {"ids": self._ids, "documents": self._docs, "metadatas": self._metas}


def test_dense_search_maps_rows_to_notechunks():
    coll = FakeDenseCollection(
        ids=["s1:n.pdf:0:0", "s1:n.pdf:0:1"],
        docs=["Plants make energy.", "Chlorophyll absorbs light."],
        metas=[
            {"topic": "biology", "session_id": "s1"},
            {"topic": "biology", "session_id": "s1"},
        ],
    )
    chunks = retriever.search("photosynthesis", top_k=5, collection=coll, mode="dense")

    assert len(chunks) == 2
    assert chunks[0].chunk_id == "s1:n.pdf:0:0"
    assert chunks[0].topic == "biology"
    assert chunks[0].content == "Plants make energy."


def test_empty_collection_returns_empty_list():
    coll = FakeHybridCollection(ids=[], docs=[], metas=[])
    assert retriever.search("anything", collection=coll) == []


def test_session_filter_passed_through_in_dense():
    coll = FakeDenseCollection(ids=["s2:n:0:0"], docs=["text"], metas=[{"topic": "t", "session_id": "s2"}])
    retriever.search("topic", session_id="s2", collection=coll, mode="dense")
    assert coll.last_where == {"session_id": "s2"}


def test_hybrid_returns_notechunks(monkeypatch):
    monkeypatch.setattr(retriever.settings, "RERANK_ENABLED", False)
    coll = FakeHybridCollection(
        ids=["c0", "c1", "c2"],
        docs=[
            "Photosynthesis converts light energy in plants.",
            "Cellular respiration releases energy as ATP.",
            "Newton's laws describe motion and force.",
        ],
        metas=[{"topic": "bio", "session_id": "s1"}] * 3,
    )
    chunks = retriever.search("energy in cells", top_k=2, collection=coll, mode="hybrid")

    assert 1 <= len(chunks) <= 2
    assert all(c.session_id == "s1" for c in chunks)
    assert all(set(c.model_dump()) == {"chunk_id", "topic", "content", "session_id"} for c in chunks)


def test_section_scoped_chunk_retrievable_by_heading(monkeypatch):
    monkeypatch.setattr(retriever.settings, "RERANK_ENABLED", False)
    coll = FakeHybridCollection(
        ids=["c0", "c1"],
        docs=[
            "Photosynthesis > Light-Dependent Reactions\nProduces ATP and NADPH in the thylakoid membrane.",
            "Photosynthesis > Calvin Cycle\nFixes carbon dioxide into glucose within the stroma.",
        ],
        metas=[
            {"topic": "bio", "session_id": "s1", "headings": "Photosynthesis > Light-Dependent Reactions"},
            {"topic": "bio", "session_id": "s1", "headings": "Photosynthesis > Calvin Cycle"},
        ],
    )
    chunks = retriever.search("light-dependent reactions", top_k=1, collection=coll, mode="hybrid")

    assert len(chunks) == 1
    assert "Light-Dependent Reactions" in chunks[0].content
    assert set(chunks[0].model_dump()) == {"chunk_id", "topic", "content", "session_id"}


def test_search_debug_exposes_pipeline_stages(monkeypatch):
    monkeypatch.setattr(retriever.settings, "RERANK_ENABLED", False)
    coll = FakeHybridCollection(
        ids=["c0", "c1"],
        docs=["light energy in plants", "motion and force"],
        metas=[{"topic": "bio", "session_id": "s1"}] * 2,
    )
    _, debug = retriever.search_debug("energy", top_k=2, collection=coll, mode="hybrid")
    assert debug["mode"] == "hybrid"
    assert set(debug) >= {"dense", "bm25", "fused", "final"}


def test_rrf_fuses_by_rank():
    order = retriever._rrf([["a", "b", "c"], ["c", "a"]])
    assert order == ["a", "c", "b"]


def test_bm25_ranks_keyword_match_first():
    ids = ["d1", "d2"]
    docs = ["the cat sat on the mat", "quantum physics and relativity"]
    ranked = retriever._bm25_rank("cat mat", ids, docs)
    assert ranked[0] == "d1"


def test_rerank_min_score_drops_weak_results(monkeypatch):
    monkeypatch.setattr(retriever.settings, "RERANK_ENABLED", True)
    monkeypatch.setattr(retriever.settings, "RERANK_MIN_SCORE", 0.0)

    class FakeModel:
        def predict(self, pairs):
            return [2.0, -1.0, 0.5][: len(pairs)]

    monkeypatch.setattr(retriever, "_get_reranker", lambda: FakeModel())
    cands = [
        {"id": "a", "doc": "x", "meta": {}},
        {"id": "b", "doc": "y", "meta": {}},
        {"id": "c", "doc": "z", "meta": {}},
    ]
    out = [c["id"] for c in retriever._rerank("q", cands)]
    assert out == ["a", "c"]
