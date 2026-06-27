from agents.generator_agent import generate_exam
from agents.validator_agent import validate_exam
from graph.state import ExamState
from mcp_server.tools.retrieval_tool import get_relevant_chunks
from schemas.exam_object import ExamObject
from schemas.note_chunk import NoteChunk


def _fetch_chunks_for_session(session_id: str, topics: list[str]) -> list[NoteChunk]:
    """Load note chunks from ChromaDB for each topic (deduped by chunk_id)."""
    by_id: dict[str, NoteChunk] = {}
    for topic in topics:
        for chunk in get_relevant_chunks(topic, session_id=session_id):
            by_id[chunk.chunk_id] = chunk
    return list(by_id.values())


def fetch_chunks(state: ExamState) -> dict:
    chunks = _fetch_chunks_for_session(state["session_id"], state["topics"])
    if not chunks:
        raise ValueError(
            f"No chunks found for session '{state['session_id']}' "
            f"and topics {state['topics']}. Upload notes first via /upload."
        )
    return {"chunks": chunks}


def generate(state: ExamState) -> dict:
    validation = state.get("validation")
    existing_exam = state.get("exam")

    exam = generate_exam(
        session_id=state["session_id"],
        topics=state["topics"],
        chunks=state["chunks"],
        num_questions=state.get("num_questions"),
        difficult=state.get("difficult", False),
        question_type=state.get("question_type", "open"),
        existing_exam=existing_exam,
        retry_feedback=validation.feedback if validation else None,
        rejected_question_ids=validation.rejected_question_ids if validation else None,
    )

    return {
        "exam": exam,
        "iteration": state.get("iteration", 0) + 1,
    }


def validate(state: ExamState) -> dict:
    exam = state["exam"]
    if exam is None:
        raise ValueError("Cannot validate: no exam in state")

    validation = validate_exam(exam, state["chunks"])

    if validation.approved:
        validated_exam = ExamObject(
            session_id=exam.session_id,
            topics=exam.topics,
            status="validated",
            questions=exam.questions,
        )
        return {"exam": validated_exam, "validation": validation}

    return {"validation": validation}
