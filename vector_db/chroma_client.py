import hashlib
import os
import re

import chromadb

from config import settings
from vector_db.embedder import get_embedding_function

_clients = {}


def _safe_session_name(session_id):
    slug = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:32].strip("_") or "s"
    return f"{slug}_{hashlib.sha1(session_id.encode()).hexdigest()[:10]}"


def _session_dir(session_id):
    return os.path.join(settings.CHROMA_PERSIST_DIR, _safe_session_name(session_id))


def get_client(session_id=None):
    session_id = session_id or settings.SESSION_ID
    if session_id not in _clients:
        _clients[session_id] = chromadb.PersistentClient(path=_session_dir(session_id))
    return _clients[session_id]


def get_collection(session_id=None):
    return get_client(session_id).get_or_create_collection(
        name=settings.CHROMA_COLLECTION,
        embedding_function=get_embedding_function(),
    )


def reset_collection(session_id=None):
    client = get_client(session_id)
    try:
        client.delete_collection(name=settings.CHROMA_COLLECTION)
    except Exception:
        pass
    return get_collection(session_id)
