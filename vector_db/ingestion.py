import os
from dataclasses import dataclass

import pymupdf4llm
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from config import settings

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]
CHUNK_TOKENS = 512
OVERLAP_TOKENS = 64


@dataclass
class ChunkRecord:
    chunk_id: str
    content: str
    topic: str
    session_id: str
    source_file: str
    page: int


def _split_markdown(md_text):
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS, strip_headers=False
    )
    token_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=CHUNK_TOKENS, chunk_overlap=OVERLAP_TOKENS
    )
    pieces = []
    for section in header_splitter.split_text(md_text):
        text = section.page_content.strip()
        if not text:
            continue
        for sub in token_splitter.split_text(text):
            sub = sub.strip()
            if sub and len(sub) >= settings.MIN_CHUNK_CHARS:
                pieces.append(sub)
    return pieces


def chunk_pdf(pdf_path, topic, session_id):
    if not os.path.isfile(pdf_path):
        raise ValueError(f"file not found: {pdf_path}")
    if not pdf_path.lower().endswith(".pdf"):
        raise ValueError(f"not a pdf: {pdf_path}")

    source_file = os.path.basename(pdf_path)
    try:
        pages = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
    except Exception as exc:
        raise ValueError(f"could not parse {source_file}: {exc}") from exc

    records = []
    index = 0
    for page_number, page_data in enumerate(pages, start=1):
        md_text = page_data.get("text", "") or ""
        for piece in _split_markdown(md_text):
            records.append(
                ChunkRecord(
                    chunk_id=f"{session_id}:{source_file}:{page_number}:{index}",
                    content=piece,
                    topic=topic,
                    session_id=session_id,
                    source_file=source_file,
                    page=page_number,
                )
            )
            index += 1
    return records


def ingest_file(path, topic, session_id, collection=None):
    from vector_db import loaders

    if not os.path.isfile(path):
        raise ValueError(f"file not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        if loaders.pdf_has_text_layer(path):
            return ingest_pdf(path, topic, session_id, collection)
        units = loaders.load_pdf_ocr(path, os.path.basename(path))
        return _store_units(units, topic, session_id, collection) if units else 0

    units = loaders.load_text(path)
    if not units:
        return 0
    return _store_units(units, topic, session_id, collection)


def _store_units(units, topic, session_id, collection):
    if collection is None:
        from vector_db.chroma_client import get_collection

        collection = get_collection()

    ids, docs, metas = [], [], []
    index = 0
    for unit in units:
        locator = unit.page or unit.slide
        if locator is None and unit.timestamp is not None:
            locator = int(unit.timestamp)
        if locator is None:
            locator = 0
        for piece in _split_markdown(unit.text):
            meta = {
                "topic": topic,
                "session_id": session_id,
                "source_file": unit.source_file,
                "transcribed": unit.transcribed,
            }
            if unit.page is not None:
                meta["page"] = unit.page
            if unit.slide is not None:
                meta["slide"] = unit.slide
            if unit.timestamp is not None:
                meta["timestamp"] = unit.timestamp
            ids.append(f"{session_id}:{unit.source_file}:{locator}:{index}")
            docs.append(piece)
            metas.append(meta)
            index += 1

    if not ids:
        return 0
    collection.upsert(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def ingest_pdf(pdf_path, topic, session_id, collection=None):
    records = chunk_pdf(pdf_path, topic, session_id)
    if not records:
        return 0

    if collection is None:
        from vector_db.chroma_client import get_collection

        collection = get_collection()

    collection.upsert(
        ids=[r.chunk_id for r in records],
        documents=[r.content for r in records],
        metadatas=[
            {
                "topic": r.topic,
                "session_id": r.session_id,
                "source_file": r.source_file,
                "page": r.page,
            }
            for r in records
        ],
    )
    return len(records)
