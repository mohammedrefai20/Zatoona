from unittest.mock import MagicMock, patch

from agents.generator_agent import generate_exam, _build_quantity_instruction
from schemas.exam_object import ExamObject, Question
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
def test_generate_exam_retry_merges_approved_questions(
    mock_get_llm,
    sample_chunks: list[NoteChunk],
    mock_generated_exam: ExamObject,
):
    """On retry, approved questions are kept via programmatic merge,
    not by trusting the LLM to reproduce them."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    # LLM returns ONLY the replacement question (not the kept one)
    replacement_q = Question(
        question_id="q-003",
        topic="ai",
        question="What is Deep Learning?",
        correct_answer="A branch of ML based on neural networks.",
        source_chunk_id="chunk-003",
    )
    llm_output = mock_generated_exam.model_copy(
        update={"questions": [replacement_q]}
    )
    mock_structured.invoke.return_value = llm_output
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
    # Should have kept q-001 + new q-003
    ids = [q.question_id for q in result.questions]
    assert "q-001" in ids  # kept from original
    assert "q-003" in ids  # replacement
    assert "q-002" not in ids  # rejected, not present

    # Prompt should contain retry instructions
    prompt = mock_structured.invoke.call_args[0][0]
    assert "RETRY INSTRUCTIONS" in prompt


@patch("agents.generator_agent._get_llm")
def test_generate_exam_with_num_questions(
    mock_get_llm,
    sample_chunks: list[NoteChunk],
    mock_generated_exam: ExamObject,
):
    """When num_questions is specified, the prompt tells the LLM
    the exact count."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_generated_exam
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    result = generate_exam(
        session_id="test-session-001",
        topics=["ai"],
        chunks=sample_chunks,
        num_questions=2,
    )

    assert isinstance(result, ExamObject)
    prompt = mock_structured.invoke.call_args[0][0]
    assert "exactly 2 question(s)" in prompt


@patch("agents.generator_agent._get_llm")
def test_generate_exam_caps_at_chunk_count(
    mock_get_llm,
    sample_chunks: list[NoteChunk],
    mock_generated_exam: ExamObject,
):
    """When num_questions exceeds available chunks, prompt explains the cap."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_generated_exam
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    result = generate_exam(
        session_id="test-session-001",
        topics=["ai"],
        chunks=sample_chunks,  # 3 chunks in fixture
        num_questions=100,
    )

    assert isinstance(result, ExamObject)
    prompt = mock_structured.invoke.call_args[0][0]
    assert "user requested 100 questions" in prompt
    assert "maximum possible" in prompt


def test_build_quantity_instruction_llm_decides():
    result = _build_quantity_instruction(
        num_questions=None, num_chunks=5, is_retry=False, num_to_replace=0
    )
    assert "Decide how many" in result


def test_build_quantity_instruction_user_specifies():
    result = _build_quantity_instruction(
        num_questions=3, num_chunks=5, is_retry=False, num_to_replace=0
    )
    assert "exactly 3" in result


def test_build_quantity_instruction_capped():
    result = _build_quantity_instruction(
        num_questions=10, num_chunks=3, is_retry=False, num_to_replace=0
    )
    assert "requested 10" in result
    assert "3" in result


def test_build_quantity_instruction_retry():
    result = _build_quantity_instruction(
        num_questions=5, num_chunks=8, is_retry=True, num_to_replace=2
    )
    assert "exactly 2 replacement" in result


@patch("agents.generator_agent._get_llm")
def test_generate_exam_with_difficult_flag(
    mock_get_llm,
    sample_chunks: list[NoteChunk],
    mock_generated_exam: ExamObject,
):
    """When difficult is True, the prompt instructs the LLM to combine multiple chunks."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_generated_exam
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    result = generate_exam(
        session_id="test-session-001",
        topics=["ai"],
        chunks=sample_chunks,
        difficult=True,
    )

    assert isinstance(result, ExamObject)
    prompt = mock_structured.invoke.call_args[0][0]
    assert "combine and synthesize information from MULTIPLE note chunks" in prompt
    assert "source_chunk_id" in prompt

