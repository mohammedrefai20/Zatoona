import os
import re

import pytest
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from vector_db import chroma_client


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


def _add(coll, cid, text, vec, sid):
    coll.add(ids=[cid], documents=[text], embeddings=[vec],
             metadatas=[{"topic": "t", "session_id": sid}])


def test_query_returns_only_own_session(isolated):
    alice = chroma_client.get_collection("alice")
    bob = chroma_client.get_collection("bob")
    _add(alice, "a1", "mitosis is cell division", [1, 0, 0, 0], "alice")
    _add(bob, "b1", "feudalism in medieval europe", [0, 1, 0, 0], "bob")

    assert alice.count() == 1
    assert bob.count() == 1
    hit = alice.query(query_embeddings=[[0, 1, 0, 0]], n_results=5)
    assert hit["ids"][0] == ["a1"]
    assert bob.get()["ids"] == ["b1"]


def test_empty_session_returns_nothing(isolated):
    alice = chroma_client.get_collection("alice")
    _add(alice, "a1", "x", [1, 0, 0, 0], "alice")
    empty = chroma_client.get_collection("nobody")
    assert empty.count() == 0
    assert empty.get()["ids"] == []


def test_same_id_same_name():
    assert chroma_client._safe_session_name("alice") == chroma_client._safe_session_name("alice")


def test_distinct_ids_distinct_names():
    assert chroma_client._safe_session_name("alice") != chroma_client._safe_session_name("bob")


def test_colliding_slugs_stay_distinct():
    assert chroma_client._safe_session_name("a b") != chroma_client._safe_session_name("a/b")


def test_odd_ids_resolve_to_one_valid_name():
    for sid in ["student a+b@uni.edu", "  spaces  ", "x" * 500, "résumé/notes"]:
        name = chroma_client._safe_session_name(sid)
        assert re.fullmatch(r"[A-Za-z0-9_-]+", name)
        assert chroma_client._safe_session_name(sid) == name


def test_two_sessions_create_separate_dirs(isolated):
    _add(chroma_client.get_collection("alice"), "a1", "x", [1, 0, 0, 0], "alice")
    _add(chroma_client.get_collection("bob"), "b1", "y", [0, 1, 0, 0], "bob")
    da, db = chroma_client._session_dir("alice"), chroma_client._session_dir("bob")
    assert da != db
    assert os.path.isdir(da) and os.path.isdir(db)


def test_operating_on_one_leaves_other_intact(isolated):
    alice = chroma_client.get_collection("alice")
    bob = chroma_client.get_collection("bob")
    _add(alice, "a1", "x", [1, 0, 0, 0], "alice")
    _add(bob, "b1", "y", [0, 1, 0, 0], "bob")
    _add(alice, "a2", "z", [1, 1, 0, 0], "alice")
    assert bob.count() == 1


def test_reset_clears_only_that_session(isolated):
    alice = chroma_client.get_collection("alice")
    bob = chroma_client.get_collection("bob")
    _add(alice, "a1", "x", [1, 0, 0, 0], "alice")
    _add(bob, "b1", "y", [0, 1, 0, 0], "bob")

    chroma_client.reset_collection("alice")

    assert chroma_client.get_collection("alice").count() == 0
    assert chroma_client.get_collection("bob").count() == 1


def test_reset_unused_session_is_noop(isolated):
    assert chroma_client.reset_collection("ghost").count() == 0


def test_get_by_id_returns_chunk_or_none(isolated):
    from vector_db import retriever

    alice = chroma_client.get_collection("alice")
    _add(alice, "a1", "mitosis notes", [1, 0, 0, 0], "alice")

    chunk = retriever.get_by_id("a1", collection=alice)
    assert chunk is not None
    assert chunk.chunk_id == "a1"
    assert chunk.content == "mitosis notes"
    assert retriever.get_by_id("missing", collection=alice) is None


def test_get_by_id_is_session_scoped(isolated):
    from vector_db import retriever

    _add(chroma_client.get_collection("alice"), "a1", "x", [1, 0, 0, 0], "alice")
    bob = chroma_client.get_collection("bob")
    assert retriever.get_by_id("a1", collection=bob) is None
