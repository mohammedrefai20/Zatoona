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

def get_relevant_chunks(topic: str) -> list[NoteChunk]:
    # simulates MCP tool — returns chunks matching the topic
    chunks = _load_chunks()
    return [c for c in chunks if c.topic.lower() == topic.lower()]