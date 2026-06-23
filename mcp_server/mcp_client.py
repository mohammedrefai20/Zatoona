import os
from schemas.note_chunk import NoteChunk

# flag to switch between mock and real MCP
# when Team A is ready set USE_REAL_MCP=true in your .env
USE_REAL_MCP = os.getenv("USE_REAL_MCP", "false").lower() == "true"

def get_chunk_by_id(chunk_id: str) -> NoteChunk | None:
    if USE_REAL_MCP:
        return _real_get_chunk_by_id(chunk_id)
    else:
        return _mock_get_chunk_by_id(chunk_id)

# ── mock (current) ───────────────────────────────────────────
def _mock_get_chunk_by_id(chunk_id: str) -> NoteChunk | None:
    from tests.team_c.mock_mcp_tool import get_chunk_by_id as mock
    return mock(chunk_id)


# ── real (tomorrow after meeting) ────────────────────────────
def _real_get_chunk_by_id(chunk_id: str) -> NoteChunk | None:
    raise NotImplementedError("real MCP not connected yet")




