from chromadb.utils import embedding_functions

from config import settings

_cached_ef = None


def _openai_ef():
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=settings.OPENAI_API_KEY,
        model_name=settings.EMBEDDING_MODEL,
    )


def _local_ef():
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.LOCAL_EMBEDDING_MODEL
    )


def _auto_ef():
    if settings.OPENAI_API_KEY:
        ef = _openai_ef()
        try:
            ef(["healthcheck"])
            return ef
        except Exception:
            print(f"OpenAI embeddings failed, using local model {settings.LOCAL_EMBEDDING_MODEL}")
    return _local_ef()


def get_embedding_function():
    global _cached_ef
    if _cached_ef is not None:
        return _cached_ef

    provider = settings.EMBEDDING_PROVIDER
    if provider == "openai":
        _cached_ef = _openai_ef()
    elif provider == "local":
        _cached_ef = _local_ef()
    elif provider == "auto":
        _cached_ef = _auto_ef()
    else:
        raise RuntimeError(f"invalid EMBEDDING_PROVIDER: {provider}")
    return _cached_ef
