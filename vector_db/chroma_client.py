import chromadb

from config import settings
from vector_db.embedder import get_embedding_function

_client = None


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _client


def get_collection():
    return get_client().get_or_create_collection(
        name=settings.CHROMA_COLLECTION,
        embedding_function=get_embedding_function(),
    )


def reset_collection():
    client = get_client()
    try:
        client.delete_collection(name=settings.CHROMA_COLLECTION)
    except Exception:
        pass
    return get_collection()
