import json

from Authentication.database import SessionLocal
from Authentication.models import StoredExam
from schemas.exam_object import ExamObject
#exam_saving

def save_exam(session_id: str, exam: ExamObject) -> None:
    """Persist a new exam for this session. Each call is a new history entry."""
    db = SessionLocal()
    try:
        db.add(StoredExam(session_id=session_id, exam_data=exam.model_dump_json()))
        db.commit()
    finally:
        db.close()


def load_exam(session_id: str) -> ExamObject | None:
    """Load the most recently generated exam for a session (for grading)."""
    db = SessionLocal()
    try:
        row = (
            db.query(StoredExam)
            .filter(StoredExam.session_id == session_id)
            .order_by(StoredExam.exam_id.desc())
            .first()
        )
        if row is None:
            return None
        return ExamObject(**json.loads(row.exam_data))
    finally:
        db.close()


def _serialize_stored_exam(row: StoredExam) -> dict:
    exam = ExamObject(**json.loads(row.exam_data))
    return {
        "exam_id": row.exam_id,
        "session_id": row.session_id,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "topics": exam.topics,
        "status": exam.status,
        "questions": [
            {
                "question_id": q.question_id,
                "topic": q.topic,
                "question": q.question,
                "question_type": q.question_type,
                "options": q.options,
            }
            for q in exam.questions
        ],
    }


def list_exam_history(session_id: str) -> list[dict]:
    db = SessionLocal()
    try:
        rows = (
            db.query(StoredExam)
            .filter(StoredExam.session_id == session_id)
            .order_by(StoredExam.created_at.desc())
            .all()
        )
        return [_serialize_stored_exam(row) for row in rows]
    finally:
        db.close()


def get_stored_exam(session_id: str, exam_id: int) -> dict | None:
    db = SessionLocal()
    try:
        row = (
            db.query(StoredExam)
            .filter(StoredExam.exam_id == exam_id, StoredExam.session_id == session_id)
            .first()
        )
        return _serialize_stored_exam(row) if row else None
    finally:
        db.close()
