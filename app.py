import shutil
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from Authentication.database import Base, engine
from Authentication.models import User
from Authentication.security import get_current_user
from agents.corrector_agent import run_corrector
from config.settings import MCP_HOST, MCP_PORT
from graph.exam_graph import ExamPipelineError, run_exam_pipeline
from mcp_server.server import start_mcp_server
from utils.exam_store import get_stored_exam, list_exam_history, load_exam, save_exam
from utils.report_writer import save_report
from vector_db import enrichment
from vector_db.chroma_client import get_collection
from vector_db.ingestion import ingest_file, ingest_text, ingest_url


def run_mcp():
    start_mcp_server(host=MCP_HOST, port=MCP_PORT)


mcp_thread = threading.Thread(target=run_mcp, daemon=True)
mcp_thread.start()
print(f"MCP server started on {MCP_HOST}:{MCP_PORT}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Leo Agent API", lifespan=lifespan)


class GenerateExamRequest(BaseModel):
    topics: list[str]
    num_questions: int | None = None
    difficult: bool = False
    question_type: str = "open"  # "open" | "mcq" | "mixed"


class AnswerItem(BaseModel):
    question_id: str
    student_answer: str


class SubmitAnswerRequest(BaseModel):
    answers: list[AnswerItem]


class ProposalModel(BaseModel):
    title: str
    url: str
    snippet: str = ""
    topic: str


class EnrichProposeRequest(BaseModel):
    limit: int | None = None


class EnrichIngestRequest(BaseModel):
    approved: list[ProposalModel]


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/upload/")
async def upload_notes(
    current_user: User = Depends(get_current_user),
    topic: str | None = Form(None),
    file: UploadFile | None = File(None),
    url: str | None = Form(None),
    text: str | None = Form(None),
):
    """Ingest notes into ChromaDB for the authenticated user.

    `topic` is optional — if omitted, an agent names it from the material's content.
    """
    session_id = current_user.session_id
    collection = get_collection(session_id)
    sources = sum(x is not None for x in (file, url, text))
    if sources != 1:
        raise HTTPException(400, "Provide exactly one of: file, url, or text")

    meta: dict = {}  # ingestion reports the resolved topic (provided or auto-named) here
    if file:
        suffix = Path(file.filename or "upload").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        try:
            count = ingest_file(tmp_path, topic, session_id, collection, meta_out=meta)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    elif url:
        result = ingest_url(url, topic, session_id, collection, meta_out=meta)
        count = len(result) if isinstance(result, list) else result
    else:
        count = ingest_text(
            text,
            "pasted-text",
            topic,
            session_id,
            source_type="text",
            collection=collection,
            meta_out=meta,
        )

    return {
        "topic": meta.get("topic") or topic or "Untitled notes",
        "chunks_stored": count,
        "message": "Notes ingested successfully",
    }


@app.post("/generate-exam/")
def generate_exam(body: GenerateExamRequest, current_user: User = Depends(get_current_user)):
    """Generate a validated exam from this user's uploaded notes in ChromaDB."""
    session_id = current_user.session_id
    if not body.topics:
        raise HTTPException(400, "topics must not be empty")

    try:
        exam = run_exam_pipeline(
            session_id=session_id,
            topics=body.topics,
            num_questions=body.num_questions,
            difficult=body.difficult,
            question_type=body.question_type,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ExamPipelineError as exc:
        raise HTTPException(422, str(exc)) from exc

    save_exam(session_id, exam)

    return {
        "session_id": session_id,
        "topics": exam.topics,
        "status": exam.status,
        "questions": [
            {
                "question_id": q.question_id,
                "topic": q.topic,
                "question": q.question,
                "question_type": q.question_type,
                "options": q.options,  # null for open questions; never the correct answer
            }
            for q in exam.questions
        ],
    }


@app.post("/submit-answer/")
def submit_answer(body: SubmitAnswerRequest, current_user: User = Depends(get_current_user)):
    """Grade answers using the user's stored exam and note chunks."""
    session_id = current_user.session_id
    exam = load_exam(session_id)
    if exam is None:
        raise HTTPException(404, "No exam found — call /generate-exam first")

    expected_ids = {q.question_id for q in exam.questions}
    provided_ids = {a.question_id for a in body.answers}
    missing = expected_ids - provided_ids
    if missing:
        raise HTTPException(
            400,
            f"Missing answers for: {', '.join(sorted(missing))}",
        )

    answers_payload = {
        "session_id": session_id,
        "answers": [a.model_dump() for a in body.answers],
    }

    report = run_corrector(exam=exam, answers=answers_payload, session_id=session_id)
    save_report(report)

    return report.model_dump()

@app.get("/get-exam/{exam_id}")
def get_exam(exam_id: int, current_user: User = Depends(get_current_user)):
    """Get an exam by its ID."""
    exam = get_stored_exam(current_user.session_id, exam_id)
    if exam is None:
        raise HTTPException(404, "No exam found")
    return exam


@app.get("/history/")
def get_history(current_user: User = Depends(get_current_user)):
    """Get the history of exams for the authenticated user."""
    session_id = current_user.session_id
    exams = list_exam_history(session_id)
    if not exams:
        raise HTTPException(404, "No exams found")
    return exams


# ── Web enrichment (opt-in) ──────────────────────────────────────────────
# Suggest web pages related to the user's uploaded topics, ingest the ones they
# approve as extra material (tagged source_type="web", fully removable). The act
# of calling these endpoints IS the opt-in — nothing hits the network otherwise.

@app.post("/enrich/propose/")
def enrich_propose(body: EnrichProposeRequest, current_user: User = Depends(get_current_user)):
    """Propose web pages related to this user's uploaded topics (no ingestion yet)."""
    session_id = current_user.session_id
    collection = get_collection(session_id)
    proposals = enrichment.propose(session_id, enabled=True, limit=body.limit, collection=collection)
    return {
        "proposals": [
            {"title": p.title, "url": p.url, "snippet": p.snippet, "topic": p.topic}
            for p in proposals
        ]
    }


@app.post("/enrich/ingest/")
def enrich_ingest(body: EnrichIngestRequest, current_user: User = Depends(get_current_user)):
    """Fetch and ingest the approved web pages as extra material for this user."""
    session_id = current_user.session_id
    collection = get_collection(session_id)
    approved = [
        enrichment.Proposal(title=p.title, url=p.url, snippet=p.snippet, topic=p.topic, selected=True)
        for p in body.approved
    ]
    outcomes = enrichment.ingest_approved(approved, session_id, enabled=True, collection=collection)
    return {"outcomes": outcomes}


@app.get("/enrich/")
def enrich_list(current_user: User = Depends(get_current_user)):
    """List the web-sourced chunks added for this user."""
    session_id = current_user.session_id
    return {"items": enrichment.list_enrichment(session_id, collection=get_collection(session_id))}


@app.delete("/enrich/")
def enrich_remove(current_user: User = Depends(get_current_user)):
    """Remove all web-sourced chunks for this user."""
    session_id = current_user.session_id
    removed = enrichment.remove_enrichment(session_id, collection=get_collection(session_id))
    return {"removed": removed}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
