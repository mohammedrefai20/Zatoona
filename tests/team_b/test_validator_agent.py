from unittest.mock import MagicMock, patch

from agents.validator_agent import _ValidationResponse, _QuestionValidation, validate_exam
from schemas.exam_object import ExamObject, Question, ValidationResult
from schemas.note_chunk import NoteChunk


def test_validate_exam_approves_grounded_question(
    valid_exam: ExamObject,
    sample_chunks: list[NoteChunk],
):
    mock_response = _ValidationResponse(
        results=[
            _QuestionValidation(
                question_id="q-001",
                approved=True,
                reason="Answer is supported by chunk-001.",
            )
        ]
    )

    with patch("agents.validator_agent._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = mock_response
        mock_llm.with_structured_output.return_value = mock_structured
        mock_get_llm.return_value = mock_llm

        result = validate_exam(valid_exam, sample_chunks)

    assert isinstance(result, ValidationResult)
    assert result.approved is True
    assert result.rejected_question_ids == []


def test_validate_exam_rejects_unsupported_answer(
    invalid_exam: ExamObject,
    sample_chunks: list[NoteChunk],
):
    mock_response = _ValidationResponse(
        results=[
            _QuestionValidation(
                question_id="q-bad",
                approved=False,
                reason="Speed of light is not mentioned in the source chunk.",
            )
        ]
    )

    with patch("agents.validator_agent._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = mock_response
        mock_llm.with_structured_output.return_value = mock_structured
        mock_get_llm.return_value = mock_llm

        result = validate_exam(invalid_exam, sample_chunks)

    assert result.approved is False
    assert "q-bad" in result.rejected_question_ids
    assert "REJECTED: q-bad" in result.feedback


def test_validate_exam_rejects_missing_source_chunk(
    sample_chunks: list[NoteChunk],
):
    exam = ExamObject(
        session_id="test-session-001",
        topics=["ai"],
        status="draft",
        questions=[
            Question(
                question_id="q-missing",
                topic="ai",
                question="Test question?",
                correct_answer="Test answer",
                source_chunk_id="chunk-999",
            )
        ],
    )

    result = validate_exam(exam, sample_chunks)

    assert result.approved is False
    assert "q-missing" in result.rejected_question_ids


def test_validate_exam_handles_multiple_source_chunks(
    sample_chunks: list[NoteChunk],
):
    exam = ExamObject(
        session_id="test-session-001",
        topics=["ai"],
        status="draft",
        questions=[
            Question(
                question_id="q-multi",
                topic="ai",
                question="Complex synthesized question?",
                correct_answer="Complex synthesized answer",
                source_chunk_id="chunk-001, chunk-002",
            )
        ],
    )

    mock_response = _ValidationResponse(
        results=[
            _QuestionValidation(
                question_id="q-multi",
                approved=True,
                reason="Answer is supported by both chunk-001 and chunk-002.",
            )
        ]
    )

    with patch("agents.validator_agent._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = mock_response
        mock_llm.with_structured_output.return_value = mock_structured
        mock_get_llm.return_value = mock_llm

        result = validate_exam(exam, sample_chunks)

    assert result.approved is True
    assert result.rejected_question_ids == []

