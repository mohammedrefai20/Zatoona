"""Opt-in, default-off web enrichment.

Derives search intent from the topics the student already supplied, searches the web with a free
no-key engine (ddgs), proposes a bounded list for review, and ingests only approved pages through the
feature-005 ``ingest_text`` sink tagged ``source_type="web"`` — so enrichment is always separable,
session-scoped, and removable. With enrichment off (the default), nothing here touches the network.
"""

from dataclasses import dataclass

from config import settings
from vector_db import ingestion


@dataclass
class Proposal:
    title: str
    url: str
    snippet: str
    topic: str
    selected: bool = False


def _get_collection(collection, session_id):
    if collection is not None:
        return collection
    from vector_db.chroma_client import get_collection

    return get_collection(session_id)


def derive_queries(session_id, collection=None):
    coll = _get_collection(collection, session_id)
    data = coll.get(include=["metadatas"])
    queries, seen = [], set()
    for meta in data.get("metadatas") or []:
        if not meta or meta.get("source_type") == "web":
            continue
        topic = meta.get("topic")
        if topic and topic not in seen:
            seen.add(topic)
            queries.append(topic)
    return queries


def search_web(queries, results_per_query=None, existing_refs=()):
    per_query = settings.ENRICH_SEARCH_RESULTS if results_per_query is None else results_per_query
    seen = set(existing_refs or ())
    proposals = []
    for query in queries:
        for result in _ddgs_search(query, per_query):
            url = result.get("href") or result.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            proposals.append(Proposal(
                title=result.get("title") or url,
                url=url,
                snippet=result.get("body") or result.get("snippet") or "",
                topic=query,
            ))
    return proposals


def _ddgs_search(query, max_results):
    # future: ddgs (DuckDuckGo) is free but rate-limits under load; ENRICH_PROVIDER is the seam to
    # swap in a self-hosted SearXNG or a keyed provider if that becomes a problem.
    from ddgs import DDGS

    return list(DDGS().text(query, max_results=max_results))


def fetch_clean(url):
    # future: a result that is itself a PDF or video is left to the caller's reason-skip here; the
    # reuse path is the feature-005 connectors (ingest_file / ingest_url), pending a decision on
    # whether such pieces stay source_type="web" or take the connector's native label.
    import trafilatura

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
    if not text or not text.strip():
        return None
    return text, _page_title(downloaded, url)


def _page_title(downloaded, url):
    import trafilatura

    try:
        meta = trafilatura.extract_metadata(downloaded)
        if meta and meta.title:
            return meta.title
    except Exception:
        pass
    return url


def propose(session_id, *, enabled, limit=None, collection=None):
    if not enabled:
        return []
    cap = settings.ENRICH_MAX_DOCS if limit is None else limit
    coll = _get_collection(collection, session_id)
    queries = derive_queries(session_id, collection=coll)
    if not queries:
        return []
    proposals = search_web(queries, existing_refs=_stored_refs(coll))
    return proposals[:cap]


def _stored_refs(collection):
    data = collection.get(include=["metadatas"])
    return {m["source_ref"] for m in (data.get("metadatas") or []) if m and m.get("source_ref")}


def ingest_approved(approved, session_id, *, enabled, collection=None):
    if not enabled or not approved:
        return []
    cap = settings.ENRICH_MAX_DOCS
    outcomes, stored = [], 0
    for proposal in approved:
        if stored >= cap:
            outcomes.append(_skip(proposal.url, f"enrichment cap reached ({cap})"))
            continue
        try:
            cleaned = fetch_clean(proposal.url)
        except Exception as exc:
            outcomes.append(_skip(proposal.url, f"could not fetch: {exc}"))
            continue
        if not cleaned:
            outcomes.append(_skip(proposal.url, "no usable content (paywalled, blocked, or empty)"))
            continue
        text, title = cleaned
        count = ingestion.ingest_text(text, proposal.url, topic=proposal.topic, session_id=session_id,
                                      source_type="web", title=title, collection=collection)
        if count:
            stored += 1
            outcomes.append({"url": proposal.url, "stored_count": count, "status": "ingested"})
        else:
            outcomes.append(_skip(proposal.url, "no usable content after extraction"))
    return outcomes


def _skip(url, reason):
    return {"url": url, "stored_count": None, "status": "skipped", "reason": reason}


def list_enrichment(session_id, collection=None):
    coll = _get_collection(collection, session_id)
    data = coll.get(where={"source_type": "web"})
    items = []
    for chunk_id, meta in zip(data.get("ids") or [], data.get("metadatas") or []):
        meta = meta or {}
        items.append({
            "chunk_id": chunk_id,
            "url": meta.get("source_ref"),
            "title": meta.get("notion_page") or meta.get("title"),
            "topic": meta.get("topic"),
        })
    return items


def remove_enrichment(session_id, collection=None):
    coll = _get_collection(collection, session_id)
    existing = coll.get(where={"source_type": "web"}).get("ids") or []
    if existing:
        coll.delete(where={"source_type": "web"})
    return len(existing)
