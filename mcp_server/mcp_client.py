import os
from schemas.note_chunk import NoteChunk

# flag to switch between mock and real MCP
# when Team A is ready set USE_REAL_MCP=true in your .env
USE_REAL_MCP = os.getenv("USE_REAL_MCP", "false").lower() == "true"

def get_relevant_chunks(topic: str) -> list[NoteChunk]:
    if USE_REAL_MCP:
        return _real_mcp_call(topic)
    else:
        return _mock_mcp_call(topic)

# ── mock (current) ───────────────────────────────────────────
def _mock_mcp_call(topic: str) -> list[NoteChunk]:
    # uses local json file — no server needed
    from tests.team_c.mock_mcp_tool import get_relevant_chunks as mock
    return mock(topic)

# ── real (tomorrow after meeting) ────────────────────────────
def _real_mcp_call(topic: str) -> list[NoteChunk]:
    # TODO: replace with Team A's real MCP server details after meeting
    # MCP_HOST and MCP_PORT will come from .env
    raise NotImplementedError("real MCP not connected yet — set USE_REAL_MCP=false until Team A is ready")