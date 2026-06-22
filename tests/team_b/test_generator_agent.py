from unittest.mock import MagicMock, patch

from agents.generator_agent import generate_exam
from schemas.exam_object import ExamObject
from schemas.note_chunk import NoteChunk


@patch("agents.generator_agent._get_llm")
def test_generate_exam_returns_valid_exam_object(
    mock_get_llm,
    sample_chunks: list[NoteChunk],
    mock_generated_exam: ExamObject,
):
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_generated_exam
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    result = generate_exam(
        session_id="test-session-001",
        topics=["ai"],
        chunks=sample_chunks,
    )

    assert isinstance(result, ExamObject)
    assert result.session_id == "test-session-001"
    assert result.topics == ["ai"]
    assert result.status == "draft"
    assert len(result.questions) == 2

    chunk_ids = {c.chunk_id for c in sample_chunks}
    for question in result.questions:
        assert question.source_chunk_id in chunk_ids


@patch("agents.generator_agent._get_llm")
def test_generate_exam_retry_keeps_approved_questions(
    mock_get_llm,
    sample_chunks: list[NoteChunk],
    mock_generated_exam: ExamObject,
):
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    revised_exam = mock_generated_exam.model_copy(
        update={
            "questions": [
                mock_generated_exam.questions[0],
                mock_generated_exam.questions[1].model_copy(
                    update={"correct_answer": "ATP and NADPH from light reactions"}
                ),
            ]
        }
    )
    mock_structured.invoke.return_value = revised_exam
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    result = generate_exam(
        session_id="test-session-001",
        topics=["ai"],
        chunks=sample_chunks,
        existing_exam=mock_generated_exam,
        retry_feedback="REJECTED: q-002: answer not supported",
        rejected_question_ids=["q-002"],
    )

    assert result.status == "draft"
    mock_structured.invoke.assert_called_once()
    prompt = mock_structured.invoke.call_args[0][0]
    assert "retry" in prompt.lower() or "Replace only the rejected" in prompt
