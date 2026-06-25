import os
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from vector_db import chunking, docling_parser, loaders


@dataclass
class ChunkRecord:
    chunk_id: str
    content: str
    topic: str
    session_id: str
    source_file: str
    page: int


def _get_collection(collection, session_id):
    if collection is not None:
        return collection
    from vector_db.chroma_client import get_collection

    return get_collection(session_id)


def ingest_file(path, topic, session_id, collection=None):
    if not os.path.isfile(path):
        raise ValueError(f"file not found: {path}")

    if docling_parser.is_document(path):
        return _ingest_document(path, topic, session_id, collection)
    if loaders.is_media(path):
        units = loaders.load_media(path)
        return _store_units(units, topic, session_id, collection)

    ext = os.path.splitext(path)[1].lower()
    raise ValueError(
        f"unsupported file type: {ext}. supported documents: "
        f"{' '.join(sorted(docling_parser.SUPPORTED_DOC_EXTS))}; media: {loaders.SUPPORTED_MEDIA}"
    )


def _ingest_document(path, topic, session_id, collection):
    source = os.path.basename(path)
    dl_doc = docling_parser.parse(path)
    transcribed = docling_parser.is_scanned(path)
    chunks = chunking.chunk(dl_doc, source, transcribed=transcribed)
    return _store_chunks(chunks, topic, session_id, collection)


def _store_chunks(chunks, topic, session_id, collection, source_type="file",
                  source_ref=None, notion_page=None):
    if not chunks:
        return 0
    collection = _get_collection(collection, session_id)

    ids, docs, metas = [], [], []
    for index, ch in enumerate(chunks):
        locator = ch.page if ch.page is not None else 0
        meta = {
            "topic": topic,
            "session_id": session_id,
            "source_file": ch.source_file,
            "transcribed": ch.transcribed,
            "source_type": source_type,
        }
        if source_ref:
            meta["source_ref"] = source_ref
        if notion_page:
            meta["notion_page"] = notion_page
        if ch.page is not None:
            meta["slide" if ch.source_file.lower().endswith(".pptx") else "page"] = ch.page
        if ch.headings:
            meta["headings"] = " > ".join(ch.headings)
        ids.append(f"{session_id}:{ch.source_file}:{locator}:{index}")
        docs.append(ch.content)
        metas.append(meta)

    collection.upsert(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def _token_splitter():
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=settings.CHUNK_MAX_TOKENS, chunk_overlap=64
    )


def _store_units(units, topic, session_id, collection, source_type="file", source_ref=None):
    splitter = _token_splitter()
    ids, docs, metas = [], [], []
    index = 0
    for unit in units:
        locator = int(unit.timestamp) if unit.timestamp is not None else 0
        for piece in splitter.split_text(unit.text):
            piece = piece.strip()
            if not piece or len(piece) < settings.MIN_CHUNK_CHARS:
                continue
            meta = {
                "topic": topic,
                "session_id": session_id,
                "source_file": unit.source_file,
                "transcribed": unit.transcribed,
                "source_type": source_type,
            }
            if source_ref:
                meta["source_ref"] = source_ref
            if unit.timestamp is not None:
                meta["timestamp"] = unit.timestamp
            ids.append(f"{session_id}:{unit.source_file}:{locator}:{index}")
            docs.append(piece)
            metas.append(meta)
            index += 1

    if not ids:
        return 0
    collection = _get_collection(collection, session_id)
    collection.upsert(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def ingest_text(text, source_ref, topic, session_id, source_type, *,
                title=None, transcribed=False, collection=None):
    if not text or not text.strip():
        return 0
    source_file = title or source_ref or source_type
    dl_doc = docling_parser.parse_text(text, name=source_file)
    chunks = chunking.chunk(dl_doc, source_file, transcribed=transcribed)
    return _store_chunks(chunks, topic, session_id, collection,
                         source_type=source_type, source_ref=source_ref, notion_page=title)


def ingest_url(url, topic, session_id, collection=None):
    from vector_db import youtube

    kind, ident = youtube.parse_target(url)
    if kind == "video":
        return _process_video(ident, url, topic, session_id, collection)["stored_count"] or 0
    return _ingest_playlist(url, topic, session_id, collection)


def _ingest_playlist(playlist_url, topic, session_id, collection):
    from vector_db import youtube

    video_ids = youtube.list_playlist(playlist_url)
    outcomes = []
    for video_id in video_ids:
        ref = f"https://www.youtube.com/watch?v={video_id}"
        outcomes.append(_process_video(video_id, ref, topic, session_id, collection))

    # future: len == cap also fires for a playlist that happens to be exactly cap-length;
    # a precise notice needs the pre-cap total, which flat enumeration doesn't return here.
    if len(video_ids) >= settings.YOUTUBE_PLAYLIST_MAX:
        outcomes.append({
            "ref": playlist_url, "stored_count": None, "status": "capped",
            "reason": f"playlist capped at {settings.YOUTUBE_PLAYLIST_MAX} videos",
        })
    return outcomes


def _process_video(video_id, source_ref, topic, session_id, collection):
    from vector_db import youtube

    try:
        units = youtube.fetch_transcript(video_id)
        if not units and settings.YOUTUBE_ASR_FALLBACK:
            units = youtube.audio_fallback(video_id)
    except (ValueError, RuntimeError) as exc:
        return {"ref": source_ref, "stored_count": None, "status": "skipped", "reason": str(exc)}

    if not units:
        return {"ref": source_ref, "stored_count": None, "status": "skipped",
                "reason": "no captions available and audio transcription is disabled"}

    stored = _store_units(units, topic, session_id, collection,
                          source_type="youtube", source_ref=source_ref)
    return {"ref": source_ref, "stored_count": stored, "status": "ingested"}


def ingest_pdf(pdf_path, topic, session_id, collection=None):
    return _ingest_document(pdf_path, topic, session_id, collection)


def chunk_pdf(pdf_path, topic, session_id):
    if not os.path.isfile(pdf_path):
        raise ValueError(f"file not found: {pdf_path}")
    if not pdf_path.lower().endswith(".pdf"):
        raise ValueError(f"not a pdf: {pdf_path}")

    source = os.path.basename(pdf_path)
    dl_doc = docling_parser.parse(pdf_path)
    chunks = chunking.chunk(dl_doc, source, transcribed=docling_parser.is_scanned(pdf_path))

    records = []
    for index, ch in enumerate(chunks):
        page = ch.page if ch.page is not None else 0
        records.append(
            ChunkRecord(
                chunk_id=f"{session_id}:{source}:{page}:{index}",
                content=ch.content,
                topic=topic,
                session_id=session_id,
                source_file=source,
                page=page,
            )
        )
    return records
