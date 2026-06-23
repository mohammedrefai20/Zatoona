import json
from pathlib import Path
from schemas.note_chunk import NoteChunk

# loads mock chunks once from file
_mock_chunks = None

def _load_chunks():
    global _mock_chunks
    if _mock_chunks is None:
        path = Path(__file__).parent / "mock_data/mock_mcp_response.json"
        with open(path) as f:
            data = json.load(f)
        _mock_chunks = [NoteChunk(**c) for c in data["chunks"]]
    return _mock_chunks

def get_chunk_by_id(chunk_id: str) -> NoteChunk | None:
    chunks = _load_chunks()
    for c in chunks:
        if c.chunk_id == chunk_id:
            return c
    return None