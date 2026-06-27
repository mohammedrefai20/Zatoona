"""Regression test for the exam persistence bug.

Before the fix, generating an exam 500'd with:
  NotNullViolation: null value in column "exam_id" of relation "stored_exams"
because exam_id was nullable=False with autoincrement on a non-PK column.

This test runs the real exam_store against an isolated SQLite DB and verifies:
  - exam_id auto-generates (no NOT NULL violation),
  - a session can hold MANY exams (history works),
  - load_exam returns the most recently generated exam.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Authentication.database import Base
import utils.exam_store as exam_store
from schemas.exam_object import ExamObject, Question


def _exam(session_id: str, qid: str, q: str) -> ExamObject:
    return ExamObject(
        session_id=session_id,
        topics=["ai"],
        status="validated",
        questions=[Question(question_id=qid, topic="ai", question=q, correct_answer="a", source_chunk_id="c1")],
    )


@pytest.fixture
def sqlite_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(exam_store, "SessionLocal", TestSession)
    yield


def test_save_exam_autogenerates_id_and_keeps_history(sqlite_db):
    sid = "session-xyz"

    # Two generations for the same session — must NOT raise, must both persist.
    exam_store.save_exam(sid, _exam(sid, "q-001", "First exam question?"))
    exam_store.save_exam(sid, _exam(sid, "q-002", "Second exam question?"))

    history = exam_store.list_exam_history(sid)
    assert len(history) == 2, "each generate should be its own history entry"

    ids = [h["exam_id"] for h in history]
    assert all(isinstance(i, int) for i in ids), "exam_id must be auto-generated, not NULL"
    assert len(set(ids)) == 2, "exam_ids must be distinct"

    # load_exam (used by grading) returns the most recent exam.
    latest = exam_store.load_exam(sid)
    assert latest is not None
    assert latest.questions[0].question_id == "q-002"

    # get_stored_exam by id round-trips.
    one = exam_store.get_stored_exam(sid, ids[0])
    assert one is not None and one["exam_id"] == ids[0]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
