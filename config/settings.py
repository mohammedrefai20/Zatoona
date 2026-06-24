import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "auto").lower()
LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION_NAME", "student_notes")

MCP_HOST = os.getenv("MCP_SERVER_HOST", "localhost")
MCP_PORT = int(os.getenv("MCP_SERVER_PORT", "8000"))

RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "hybrid").lower()
RETRIEVAL_CANDIDATE_K = int(os.getenv("RETRIEVAL_CANDIDATE_K", "20"))
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "true").lower() == "true"
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

_min_score = os.getenv("RERANK_MIN_SCORE", "").strip()
RERANK_MIN_SCORE = float(_min_score) if _min_score else None
MIN_CHUNK_CHARS = int(os.getenv("MIN_CHUNK_CHARS", "0"))

ASR_PROVIDER = os.getenv("ASR_PROVIDER", "local").lower()
ASR_MODEL = os.getenv("ASR_MODEL", "base")
VIDEO_ENABLED = os.getenv("VIDEO_ENABLED", "false").lower() == "true"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CHUNK_MODE = os.getenv("CHUNK_MODE", "hybrid").lower()
CHUNK_MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", "512"))
DOCLING_DO_OCR = os.getenv("DOCLING_DO_OCR", "true").lower() == "true"
DOCLING_OCR_ENGINE = os.getenv("DOCLING_OCR_ENGINE", "rapidocr").lower()
DOCLING_BITMAP_AREA_THRESHOLD = float(os.getenv("DOCLING_BITMAP_AREA_THRESHOLD", "0.05"))
SEMANTIC_SIM_THRESHOLD = float(os.getenv("SEMANTIC_SIM_THRESHOLD", "0.5"))

SESSION_RESET = os.getenv("SESSION_RESET_ON_START", "true").lower() == "true"

UI_PORT = int(os.getenv("UI_PORT", "8501"))
