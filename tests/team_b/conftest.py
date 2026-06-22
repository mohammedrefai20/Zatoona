import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from schemas.exam_object import ExamObject, Question, ValidationResult
from schemas.note_chunk import NoteChunk

MOCK_DATA_PATH = Path(__file__).parent / "mock_data" / "mock_mcp_response.json"


@pytest.fixture
def sample_chunks() -> list[NoteChunk]:
    with MOCK_DATA_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return [NoteChunk(**c) for c in data["chunks"][:3]]


@pytest.fixture
def valid_exam(sample_chunks: list[NoteChunk]) -> ExamObject:
    return ExamObject(
        session_id="test-session-001",
        topics=["ai"],
        status="draft",
        questions=[
            Question(
                question_id="q-001",
                topic="ai",
                question="What does Artificial Intelligence (AI) refer to?",
                correct_answer="The simulation of human intelligence processes by machines, especially computer systems.",
                source_chunk_id="chunk-001",
            )
        ],
    )


@pytest.fixture
def invalid_exam(sample_chunks: list[NoteChunk]) -> ExamObject:
    return ExamObject(
        session_id="test-session-001",
        topics=["ai"],
        status="draft",
        questions=[
            Question(
                question_id="q-bad",
                topic="ai",
                question="What is the speed of light?",
                correct_answer="299,792,458 m/s",
                source_chunk_id="chunk-001",
            )
        ],
    )


@pytest.fixture
def mock_generated_exam() -> ExamObject:
    return ExamObject(
        session_id="test-session-001",
        topics=["ai"],
        status="draft",
        questions=[
            Question(
                question_id="q-001",
                topic="ai",
                question="What does Artificial Intelligence (AI) refer to?",
                correct_answer="The simulation of human intelligence processes by machines, especially computer systems.",
                source_chunk_id="chunk-001",
            ),
            Question(
                question_id="q-002",
                topic="ai",
                question="What is Machine Learning (ML)?",
                correct_answer="A subset of AI that provides systems the ability to automatically learn and improve from experience.",
                source_chunk_id="chunk-002",
            ),
        ],
    )
