import json
import os
from pathlib import Path
from schemas.exam_object import ExamObject

USE_REAL_EXAM = os.getenv("USE_REAL_EXAM", "false").lower() == "true"

def load_exam(
    session_id: str = None,
    topics: list[str] = None,
    num_questions: int = None,
    difficult: bool = False
) -> ExamObject:
    if USE_REAL_EXAM:
        return _real_exam_load(session_id, topics, num_questions, difficult)
    else:
        return _mock_exam_load()

def _mock_exam_load() -> ExamObject:
    path = Path("tests/team_c/mock_data/mock_exam_object.json")
    with open(path) as f:
        data = json.load(f)
    return ExamObject(**data)

def _real_exam_load(
    session_id: str = "test-session-001",
    topics: list[str] = None,
    num_questions: int = 3,
    difficult: bool = False
) -> ExamObject:
    if topics is None:
        topics = ["ai", "python"]
    from graph.exam_graph import run_exam_pipeline
    return run_exam_pipeline(
        session_id=session_id,
        topics=topics,
        num_questions=num_questions,
        difficult=difficult
    )