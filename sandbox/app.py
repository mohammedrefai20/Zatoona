import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from config import settings
from vector_db import chroma_client, embedder, retriever
from vector_db.ingestion import ingest_file
from mcp_server.tools.retrieval_tool import get_relevant_chunks

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
    st.write(f"Embedding provider: `{settings.EMBEDDING_PROVIDER}`")
    st.write(f"Active embedder: `{active_provider()}`")
    st.write(f"Retrieval mode: `{settings.RETRIEVAL_MODE}`")
    st.write(f"Rerank enabled: `{settings.RERANK_ENABLED}`")
    st.write(f"Rerank min score: `{settings.RERANK_MIN_SCORE}`")
    st.write(f"Min chunk chars: `{settings.MIN_CHUNK_CHARS}`")
    try:
        st.metric("Chunks in collection", chroma_client.get_collection().count())
    except Exception as exc:
        st.error(f"Collection unavailable: {exc}")

    if st.button("Reset collection"):
        chroma_client.reset_collection()
        st.success("Collection reset.")
        st.rerun()


st.header("1) Ingest a PDF")
col_a, col_b = st.columns(2)
with col_a:
    topic = st.text_input("Topic", value="biology")
with col_b:
    session_id = st.text_input("Session ID", value="sandbox-session")

uploaded = st.file_uploader(
    "Upload study files",
    type=["pdf", "md", "txt", "pptx", "mp3", "wav", "m4a", "mp4"],
    accept_multiple_files=True,
)
st.caption("PDF (text or scanned), Markdown, text, PowerPoint, audio, video. "
           "Scanned PDFs and recordings are transcribed and approximate.")

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

    coll = chroma_client.get_collection()
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
        badge = " · transcribed" if meta.get("transcribed") else ""
        with st.expander(f"{cid}  ·  {loc}{badge}"):
            st.write(doc)


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
