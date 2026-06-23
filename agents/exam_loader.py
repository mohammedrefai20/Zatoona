import json
import os
from pathlib import Path
from schemas.exam_object import ExamObject

# flag to switch between mock file and real Team B output
# when Team B is ready set USE_REAL_EXAM=true in your .env
USE_REAL_EXAM = os.getenv("USE_REAL_EXAM", "false").lower() == "true"

def load_exam() -> ExamObject:
    if USE_REAL_EXAM:
        return _real_exam_load()
    else:
        return _mock_exam_load()

# ── mock (current) ───────────────────────────────────────────
def _mock_exam_load() -> ExamObject:
    # loads from local json file — no Team B needed
    path = Path("tests/team_c/mock_data/mock_exam_object.json")
    with open(path) as f:
        data = json.load(f)
    return ExamObject(**data)

# ── real (after meeting with Team B) ─────────────────────────
def _real_exam_load() -> ExamObject:
    # TODO: import Team B's LangGraph pipeline and get the exam object from it
    # example: from graph.exam_graph import run_exam_pipeline
    #          return run_exam_pipeline(notes, topics)
    raise NotImplementedError("real exam pipeline not connected yet — set USE_REAL_EXAM=false until Team B is ready")