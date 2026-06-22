import json
from pathlib import Path

from agents.generator_agent import generate_exam
from agents.validator_agent import validate_exam
from config.settings import MOCK_MCP_PATH
from graph.state import ExamState
from schemas.exam_object import ExamObject
from schemas.note_chunk import NoteChunk


def _load_mock_chunks(session_id: str, topics: list[str]) -> list[NoteChunk]:
    path = Path(MOCK_MCP_PATH)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    chunks = [NoteChunk(**chunk) for chunk in data["chunks"]]
    topic_set = {t.lower() for t in topics}

    return [
        c
        for c in chunks
        if c.session_id == session_id and c.topic.lower() in topic_set
    ]


def fetch_chunks(state: ExamState) -> dict:
    chunks = _load_mock_chunks(state["session_id"], state["topics"])
    if not chunks:
        raise ValueError(
            f"No chunks found for session '{state['session_id']}' "
            f"and topics {state['topics']}"
        )
    return {"chunks": chunks}


def generate(state: ExamState) -> dict:
    validation = state.get("validation")
    existing_exam = state.get("exam")

    exam = generate_exam(
        session_id=state["session_id"],
        topics=state["topics"],
        chunks=state["chunks"],
        existing_exam=existing_exam,
        retry_feedback=validation.feedback if validation else None,
        rejected_question_ids=validation.rejected_question_ids if validation else None,
    )

    return {
        "exam": exam,
        "iteration": state["iteration"] + 1,
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
