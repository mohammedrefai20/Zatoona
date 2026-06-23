from config import settings
from schemas.note_chunk import NoteChunk
from vector_db import retriever


def get_relevant_chunks(topic: str, top_k: int = settings.RETRIEVAL_TOP_K) -> list[NoteChunk]:
    return retriever.search(topic, top_k=top_k)


def register(mcp):
    mcp.tool()(get_relevant_chunks)
