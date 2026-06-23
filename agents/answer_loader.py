import json
import os
from pathlib import Path

USE_REAL_ANSWERS = os.getenv("USE_REAL_ANSWERS", "false").lower() == "true"

def load_answers() -> dict:
    if USE_REAL_ANSWERS:
        return _real_answers_load()
    else:
        return _mock_answers_load()

# ── mock (current) ───────────────────────────────────────────
def _mock_answers_load() -> dict:
    # loads from local json file — no UI needed yet
    path = Path("tests/team_c/mock_data/mock_student_answers.json")
    with open(path) as f:
        return json.load(f)

# ── real (phase 7 — after UI is built) ───────────────────────
def _real_answers_load() -> dict:
    # TODO: get answers from UI input
    raise NotImplementedError("real answers not connected yet — set USE_REAL_ANSWERS=false until UI is ready")