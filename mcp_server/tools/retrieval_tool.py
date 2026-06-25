from config import settings
from schemas.note_chunk import NoteChunk
from vector_db import chroma_client, retriever


def get_relevant_chunks(topic: str, top_k: int = settings.RETRIEVAL_TOP_K) -> list[NoteChunk]:
    collection = chroma_client.get_collection(settings.SESSION_ID)
    return retriever.search(topic, top_k=top_k, session_id=settings.SESSION_ID, collection=collection)


def get_chunk_by_id(chunk_id: str) -> NoteChunk | None:
    collection = chroma_client.get_collection(settings.SESSION_ID)
    return retriever.get_by_id(chunk_id, session_id=settings.SESSION_ID, collection=collection)


def register(mcp):
    mcp.tool()(get_relevant_chunks)
    mcp.tool()(get_chunk_by_id)
