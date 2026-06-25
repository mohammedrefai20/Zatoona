import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from config import settings
from vector_db import chroma_client, embedder, enrichment, retriever
from vector_db.ingestion import ingest_file, ingest_text, ingest_url
from mcp_server.tools.retrieval_tool import get_relevant_chunks, get_chunk_by_id

st.set_page_config(page_title="Notes Sandbox", layout="wide")
st.title("Notes Ingestion & Retrieval Sandbox")


def active_provider():
    try:
        ef = embedder.get_embedding_function()
        return type(ef).__name__
    except Exception as exc:
        return f"unavailable ({type(exc).__name__})"


with st.sidebar:
    st.header("Status")
    session_id = st.text_input("Session ID", value=settings.SESSION_ID)
    settings.SESSION_ID = session_id
    st.write(f"Embedding provider: `{settings.EMBEDDING_PROVIDER}`")
    st.write(f"Active embedder: `{active_provider()}`")
    st.write(f"Chunk mode: `{settings.CHUNK_MODE}`")
    st.write(f"OCR engine: `{settings.DOCLING_OCR_ENGINE}`")
    st.write(f"Retrieval mode: `{settings.RETRIEVAL_MODE}`")
    st.write(f"Rerank enabled: `{settings.RERANK_ENABLED}`")
    st.write(f"Rerank min score: `{settings.RERANK_MIN_SCORE}`")
    st.write(f"Min chunk chars: `{settings.MIN_CHUNK_CHARS}`")
    try:
        st.metric("Chunks in session", chroma_client.get_collection(session_id).count())
    except Exception as exc:
        st.error(f"Collection unavailable: {exc}")

    if st.button("Reset session"):
        chroma_client.reset_collection(session_id)
        st.success("Session reset.")
        st.rerun()


st.header("1) Ingest documents & recordings")
topic = st.text_input("Topic", value="biology")

uploaded = st.file_uploader(
    "Upload study files",
    type=["pdf", "docx", "pptx", "md", "txt", "html", "htm",
          "png", "jpg", "jpeg", "mp3", "wav", "m4a", "mp4"],
    accept_multiple_files=True,
)
st.caption("Documents (PDF text/scanned, Word, PowerPoint, Markdown, text, HTML, images) are parsed "
           "by Docling; audio/video are transcribed. Scanned/handwritten pages and recordings are "
           "transcribed and approximate.")

if uploaded and st.button("Ingest"):
    for up in uploaded:
        tmp_path = os.path.join(tempfile.gettempdir(), up.name)
        with open(tmp_path, "wb") as fh:
            fh.write(up.getbuffer())
        try:
            with st.spinner(f"Processing {up.name}..."):
                stored = ingest_file(tmp_path, topic=topic, session_id=session_id)
            if stored:
                st.success(f"{up.name}: stored {stored} chunk(s).")
            else:
                st.warning(f"{up.name}: no usable content found.")
        except Exception as exc:
            st.error(f"{up.name}: {exc}")

    coll = chroma_client.get_collection(session_id)
    data = coll.get(where={"session_id": session_id}, include=["documents", "metadatas"])
    st.subheader(f"Stored chunks ({len(data['ids'])})")
    for cid, doc, meta in zip(data["ids"], data["documents"], data["metadatas"]):
        if meta.get("page"):
            loc = f"page {meta['page']}"
        elif meta.get("slide"):
            loc = f"slide {meta['slide']}"
        elif meta.get("timestamp") is not None:
            loc = f"t={meta['timestamp']}s"
        else:
            loc = ""
        stype = meta.get("source_type", "file")
        badge = (f" · {stype}" if stype != "file" else "")
        badge += " · transcribed" if meta.get("transcribed") else ""
        headings = f"  ·  {meta['headings']}" if meta.get("headings") else ""
        with st.expander(f"{cid}  ·  {loc}{badge}{headings}"):
            st.write(doc)


st.header("1b) Add external sources")


def render_youtube_result(result):
    if isinstance(result, int):
        if result:
            st.success(f"Stored {result} chunk(s) from the video.")
        else:
            st.warning("No usable transcript (captions absent and ASR fallback off or unavailable).")
        return
    ingested = [o for o in result if o["status"] == "ingested"]
    st.success(f"Playlist: {len(ingested)} video(s) ingested.")
    for o in result:
        if o["status"] == "ingested":
            st.write(f"✅ {o['ref']} — {o['stored_count']} chunk(s)")
        elif o["status"] == "capped":
            st.info(o["reason"])
        else:
            st.write(f"⏭️ {o['ref']} — skipped: {o['reason']}")


yt_url = st.text_input("Add a link (YouTube video or playlist)", value="")
if st.button("Add link") and yt_url.strip():
    try:
        with st.spinner("Fetching transcript(s)..."):
            render_youtube_result(ingest_url(yt_url.strip(), topic=topic, session_id=session_id))
    except Exception as exc:
        st.error(f"{yt_url}: {exc}")
st.caption("YouTube transcripts are fetched free (no API key). Auto-generated captions and the "
           "audio fallback are approximate and flagged 'transcribed'. A playlist link ingests every "
           "video with a per-video outcome.")

with st.expander("Add a Notion page (paste its text)"):
    st.caption("In normal use the connected Notion MCP fetches the page; paste here to test the path.")
    n_title = st.text_input("Page title", value="", key="notion_title")
    n_ref = st.text_input("Page link or id (provenance)", value="", key="notion_ref")
    n_text = st.text_area("Page text", value="", key="notion_text")
    if st.button("Add Notion text") and n_text.strip():
        title = n_title or "Notion page"
        try:
            stored = ingest_text(n_text, n_ref or title, topic=topic, session_id=session_id,
                                 source_type="notion", title=title)
            if stored:
                st.success(f"Stored {stored} chunk(s) from Notion page '{title}'.")
            else:
                st.warning("No usable text found on that page.")
        except Exception as exc:
            st.error(f"Notion: {exc}")


st.header("1c) Web enrichment (opt-in, default off)")
enrich_on = st.checkbox(
    "Enable web enrichment for this session",
    value=settings.ENRICH_ENABLED,
    help="Default off. When on, searches the web (free, no key) for the topics in your own sources and "
         "proposes pages to review. Nothing is stored until you approve it; enrichment is labelled "
         "source_type=web and can be removed without touching your own material.",
)

if st.button("Propose sources"):
    if not enrich_on:
        st.info("Enable web enrichment first.")
    else:
        try:
            with st.spinner("Searching the web for your topics..."):
                st.session_state["proposals"] = enrichment.propose(session_id, enabled=True)
            if not st.session_state["proposals"]:
                st.warning("Nothing suitable found — add your own sources first, or no good matches.")
        except Exception as exc:
            st.error(f"Search unavailable: {exc}")

proposals = st.session_state.get("proposals", [])
if proposals:
    st.write(f"{len(proposals)} proposed source(s) — tick the ones to add:")
    picks = []
    for i, p in enumerate(proposals):
        picks.append(st.checkbox(f"{p.title}  ·  _{p.topic}_", key=f"prop_{i}"))
        st.caption(f"{p.url} — {p.snippet}")
    if st.button("Add approved"):
        approved = [p for p, picked in zip(proposals, picks) if picked]
        if not approved:
            st.info("No proposals selected.")
        else:
            with st.spinner(f"Fetching and ingesting {len(approved)} page(s)..."):
                outcomes = enrichment.ingest_approved(approved, session_id, enabled=enrich_on)
            for o in outcomes:
                if o["status"] == "ingested":
                    st.success(f"✅ {o['url']} — {o['stored_count']} chunk(s)")
                else:
                    st.write(f"⏭️ {o['url']} — skipped: {o['reason']}")
            st.session_state["proposals"] = []

enrichment_items = enrichment.list_enrichment(session_id)
if enrichment_items:
    st.caption(f"Enrichment in this session — {len(enrichment_items)} chunk(s), labelled source_type=web:")
    for item in enrichment_items:
        st.write(f"· {item['title'] or item['url']}  —  {item['url']}")
    if st.button("Remove enrichment"):
        removed = enrichment.remove_enrichment(session_id)
        st.success(f"Removed {removed} enrichment chunk(s); your own material is untouched.")
        st.rerun()


st.header("2) Retrieve by topic")
query = st.text_input("Query / topic to search", value="energy in living cells")
top_k = st.slider("top_k", min_value=1, max_value=10, value=settings.RETRIEVAL_TOP_K)
show_stages = st.checkbox("Show retrieval pipeline stages (hybrid)", value=True)

if st.button("Search"):
    try:
        results = get_relevant_chunks(query, top_k=top_k)
        st.subheader(f"Results ({len(results)})")
        if not results:
            st.info("No chunks returned (empty collection or no match).")
        for i, c in enumerate(results, 1):
            with st.expander(f"#{i}  ·  {c.chunk_id}  ·  topic={c.topic}"):
                st.write(c.content)

        if show_stages and settings.RETRIEVAL_MODE == "hybrid":
            _, debug = retriever.search_debug(query, top_k=top_k)
            if not debug.get("empty"):
                st.subheader("Pipeline stages (chunk ids, best first)")
                s1, s2, s3, s4 = st.columns(4)
                s1.markdown("Dense");     s1.write(debug.get("dense", []))
                s2.markdown("BM25");      s2.write(debug.get("bm25", []))
                s3.markdown("Fused");     s3.write(debug.get("fused", []))
                s4.markdown("Reranked");  s4.write(debug.get("final", []))
    except Exception as exc:
        st.error(f"Search failed: {exc}")


st.header("3) Retrieve by chunk ID")
cid = st.text_input("Chunk ID", value="")
if st.button("Fetch by ID"):
    chunk = get_chunk_by_id(cid)
    if chunk is None:
        st.info("No chunk with that ID in this session.")
    else:
        st.write({"chunk_id": chunk.chunk_id, "topic": chunk.topic, "session_id": chunk.session_id})
        st.write(chunk.content)
