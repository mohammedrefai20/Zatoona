from unittest.mock import patch

import pytest

from graph.exam_graph import ExamPipelineError, run_exam_pipeline
from graph.nodes import fetch_chunks
from graph.state import ExamState
from schemas.exam_object import ExamObject, ValidationResult


def test_fetch_chunks_loads_mock_data():
    state: ExamState = {
        "session_id": "test-session-001",
        "topics": ["ai", "python"],
        "chunks": [],
        "exam": None,
        "validation": None,
        "iteration": 0,
        "max_iterations": 3,
    }

    result = fetch_chunks(state)

    assert len(result["chunks"]) >= 4
    topics = {c.topic for c in result["chunks"]}
    assert "ai" in topics
    assert "python" in topics


@patch("graph.nodes.validate_exam")
@patch("graph.nodes.generate_exam")
def test_exam_graph_happy_path(
    mock_generate,
    mock_validate,
    mock_generated_exam: ExamObject,
):
    mock_generate.return_value = mock_generated_exam
    mock_validate.return_value = ValidationResult(
        approved=True,
        rejected_question_ids=[],
        feedback="All questions approved.",
    )

    result = run_exam_pipeline(
        session_id="test-session-001",
        topics=["ai"],
    )

    assert result.status == "validated"
    assert len(result.questions) == 2
    mock_generate.assert_called_once()
    mock_validate.assert_called_once()


@patch("graph.nodes.validate_exam")
@patch("graph.nodes.generate_exam")
def test_exam_graph_reject_then_approve(
    mock_generate,
    mock_validate,
    mock_generated_exam: ExamObject,
):
    mock_generate.return_value = mock_generated_exam
    mock_validate.side_effect = [
        ValidationResult(
            approved=False,
            rejected_question_ids=["q-002"],
            feedback="REJECTED: q-002: unsupported answer",
        ),
        ValidationResult(
            approved=True,
            rejected_question_ids=[],
            feedback="All questions approved.",
        ),
    ]

    result = run_exam_pipeline(
        session_id="test-session-001",
        topics=["ai"],
    )

    assert result.status == "validated"
    assert mock_generate.call_count == 2
    assert mock_validate.call_count == 2


@patch("graph.nodes.validate_exam")
@patch("graph.nodes.generate_exam")
def test_exam_graph_max_iterations_exceeded(
    mock_generate,
    mock_validate,
    mock_generated_exam: ExamObject,
):
    mock_generate.return_value = mock_generated_exam
    mock_validate.return_value = ValidationResult(
        approved=False,
        rejected_question_ids=["q-001"],
        feedback="REJECTED: q-001: still invalid",
    )

    with pytest.raises(ExamPipelineError, match="validation failed"):
        run_exam_pipeline(
            session_id="test-session-001",
            topics=["ai"],
        )

    assert mock_generate.call_count == 3
    assert mock_validate.call_count == 3
