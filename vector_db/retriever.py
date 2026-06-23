from config import settings
from schemas.note_chunk import NoteChunk

_reranker = None


def search(topic, top_k=None, session_id=None, collection=None, mode=None):
    chunks, _ = _run(topic, top_k, session_id, collection, mode)
    return chunks


def search_debug(topic, top_k=None, session_id=None, collection=None, mode=None):
    return _run(topic, top_k, session_id, collection, mode)


def _run(topic, top_k, session_id, collection, mode):
    top_k = top_k or settings.RETRIEVAL_TOP_K
    mode = (mode or settings.RETRIEVAL_MODE).lower()

    if collection is None:
        from vector_db.chroma_client import get_collection

        collection = get_collection()

    if collection.count() == 0:
        return [], {"mode": mode, "empty": True}

    if mode == "dense":
        return _dense_search(topic, top_k, session_id, collection)
    return _hybrid_search(topic, top_k, session_id, collection)


def _dense_search(topic, top_k, session_id, collection):
    where = {"session_id": session_id} if session_id else None
    result = collection.query(query_texts=[topic], n_results=top_k, where=where)

    ids = (result.get("ids") or [[]])[0]
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]

    chunks = [_to_chunk(i, d, m, topic) for i, d, m in zip(ids, docs, metas)]
    return chunks, {"mode": "dense", "dense": ids}


def _hybrid_search(topic, top_k, session_id, collection):
    where = {"session_id": session_id} if session_id else None

    corpus = collection.get(where=where, include=["documents", "metadatas"])
    ids = corpus.get("ids", []) or []
    docs = corpus.get("documents", []) or []
    metas = corpus.get("metadatas", []) or []
    if not ids:
        return [], {"mode": "hybrid", "empty": True}

    by_id = {i: (d, m or {}) for i, d, m in zip(ids, docs, metas)}
    pool = min(settings.RETRIEVAL_CANDIDATE_K, len(ids))

    dres = collection.query(query_texts=[topic], n_results=pool, where=where)
    dense_ids = (dres.get("ids") or [[]])[0]
    bm25_ids = _bm25_rank(topic, ids, docs)[:pool]
    fused_ids = _rrf([dense_ids, bm25_ids])[:pool]

    candidates = [{"id": i, "doc": by_id[i][0], "meta": by_id[i][1]} for i in fused_ids if i in by_id]
    reranked = _rerank(topic, candidates)
    final = reranked[:top_k]

    chunks = [_to_chunk(c["id"], c["doc"], c["meta"], topic) for c in final]
    debug = {
        "mode": "hybrid",
        "dense": dense_ids,
        "bm25": bm25_ids,
        "fused": fused_ids,
        "reranked": [c["id"] for c in reranked],
        "final": [c["id"] for c in final],
    }
    return chunks, debug


def _to_chunk(chunk_id, content, meta, topic):
    meta = meta or {}
    return NoteChunk(
        chunk_id=chunk_id,
        topic=meta.get("topic", topic),
        content=content,
        session_id=meta.get("session_id", ""),
    )


def _bm25_rank(query, corpus_ids, corpus_docs):
    from rank_bm25 import BM25Okapi

    tokenized = [doc.lower().split() for doc in corpus_docs]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.lower().split())
    order = sorted(range(len(corpus_ids)), key=lambda i: scores[i], reverse=True)
    return [corpus_ids[i] for i in order]


def _rrf(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, _id in enumerate(ranking):
            scores[_id] = scores.get(_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(settings.RERANKER_MODEL)
    return _reranker


def _rerank(query, candidates):
    if not settings.RERANK_ENABLED or len(candidates) <= 1:
        return candidates
    model = _get_reranker()
    scores = model.predict([(query, c["doc"]) for c in candidates])
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    if settings.RERANK_MIN_SCORE is not None:
        ranked = [(score, c) for score, c in ranked if score >= settings.RERANK_MIN_SCORE]
    return [c for _, c in ranked]
