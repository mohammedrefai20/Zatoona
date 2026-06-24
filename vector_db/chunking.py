from dataclasses import dataclass, field

from config import settings


@dataclass
class Chunk:
    content: str
    page: int = None
    headings: list = field(default_factory=list)
    source_file: str = ""
    transcribed: bool = False


_chunker = None


def chunk(dl_doc, source_file, transcribed=False):
    if settings.CHUNK_MODE == "semantic":
        return _semantic_chunks(dl_doc, source_file, transcribed=transcribed)
    return _hybrid_chunks(dl_doc, source_file, transcribed=transcribed)


def _get_hybrid_chunker():
    global _chunker
    if _chunker is None:
        import tiktoken
        from docling.chunking import HybridChunker
        from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

        tokenizer = OpenAITokenizer(
            tokenizer=tiktoken.encoding_for_model(settings.EMBEDDING_MODEL),
            max_tokens=settings.CHUNK_MAX_TOKENS,
        )
        _chunker = HybridChunker(tokenizer=tokenizer, merge_peers=True)
    return _chunker


def _hybrid_chunks(dl_doc, source_file, transcribed=False):
    chunker = _get_hybrid_chunker()
    out = []
    for ch in chunker.chunk(dl_doc):
        content = (chunker.contextualize(ch) or "").strip()
        if not content or len(content) < settings.MIN_CHUNK_CHARS:
            continue
        out.append(
            Chunk(
                content=content,
                page=_first_page(ch),
                headings=list(getattr(ch.meta, "headings", None) or []),
                source_file=source_file,
                transcribed=transcribed,
            )
        )
    return out


def _first_page(ch):
    for item in (getattr(ch.meta, "doc_items", None) or []):
        for prov in (getattr(item, "prov", None) or []):
            page_no = getattr(prov, "page_no", None)
            if page_no is not None:
                return page_no
    return None


def _semantic_chunks(dl_doc, source_file, transcribed=False):
    # future: reuses the paid OpenAI embedder at ingest; a local embedding model would make it free.
    import tiktoken
    from docling.chunking import HierarchicalChunker

    from vector_db.embedder import get_embedding_function

    hier = HierarchicalChunker()
    units = []
    for base in hier.chunk(dl_doc):
        text = (hier.contextualize(base) or "").strip()
        if text:
            units.append((text, base))
    if not units:
        return []

    texts = [t for t, _ in units]
    vectors = get_embedding_function()(texts)
    enc = tiktoken.encoding_for_model(settings.EMBEDDING_MODEL)
    token_counts = [len(enc.encode(t)) for t in texts]

    groups = [[0]]
    group_tokens = token_counts[0]
    for i in range(1, len(units)):
        sim = _cosine(vectors[i], vectors[i - 1])
        if sim >= settings.SEMANTIC_SIM_THRESHOLD and group_tokens + token_counts[i] <= settings.CHUNK_MAX_TOKENS:
            groups[-1].append(i)
            group_tokens += token_counts[i]
        else:
            groups.append([i])
            group_tokens = token_counts[i]

    out = []
    for group in groups:
        content = "\n".join(texts[i] for i in group).strip()
        if not content or len(content) < settings.MIN_CHUNK_CHARS:
            continue
        head = units[group[0]][1]
        out.append(
            Chunk(
                content=content,
                page=_first_page(head),
                headings=list(getattr(head.meta, "headings", None) or []),
                source_file=source_file,
                transcribed=transcribed,
            )
        )
    return out


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
