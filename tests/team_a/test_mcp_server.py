import pytest

from schemas.note_chunk import NoteChunk
from mcp_server.tools import retrieval_tool


def test_notechunk_contract_is_exactly_four_fields():
    assert set(NoteChunk.model_fields) == {"chunk_id", "topic", "content", "session_id"}


def test_notechunk_forbids_extra_fields():
    with pytest.raises(Exception):
        NoteChunk(chunk_id="c", topic="t", content="x", session_id="s", page=3)


def test_get_relevant_chunks_returns_list_of_notechunks(monkeypatch):
    sample = [NoteChunk(chunk_id="s1:n:0:0", topic="bio", content="cells", session_id="s1")]
    monkeypatch.setattr(retrieval_tool.retriever, "search", lambda *a, **k: sample)

    result = retrieval_tool.get_relevant_chunks("biology")

    assert isinstance(result, list)
    assert all(isinstance(c, NoteChunk) for c in result)
    assert result[0].chunk_id == "s1:n:0:0"


def test_get_relevant_chunks_empty_is_empty_list(monkeypatch):
    monkeypatch.setattr(retrieval_tool.retriever, "search", lambda *a, **k: [])
    assert retrieval_tool.get_relevant_chunks("nothing-here") == []


def test_tool_registers_on_a_fastmcp_instance():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("test")
    retrieval_tool.register(mcp)


def test_init_collection_resets_when_enabled(monkeypatch):
    from mcp_server import server

    calls = []
    monkeypatch.setattr(server.settings, "SESSION_RESET", True)
    monkeypatch.setattr(server.chroma_client, "reset_collection", lambda: calls.append("reset"))
    monkeypatch.setattr(server.chroma_client, "get_collection", lambda: calls.append("get"))

    server.init_collection()
    assert calls == ["reset"]


def test_init_collection_reuses_when_disabled(monkeypatch):
    from mcp_server import server

    calls = []
    monkeypatch.setattr(server.settings, "SESSION_RESET", False)
    monkeypatch.setattr(server.chroma_client, "reset_collection", lambda: calls.append("reset"))
    monkeypatch.setattr(server.chroma_client, "get_collection", lambda: calls.append("get"))

    server.init_collection()
    assert calls == ["get"]
