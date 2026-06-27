"""MCQ support — additive, default-open. TDD across schema + generator + validator + corrector.
All LLM calls are mocked; no network or heavy deps required.
"""
from unittest.mock import MagicMock, patch

from schemas.exam_object import ExamObject, Question
from schemas.note_chunk import NoteChunk


def _chunk(cid="c1"):
    return NoteChunk(chunk_id=cid, topic="ai", content="Paris is the capital of France.", session_id="s1")


def _mock_llm(return_exam):
    structured = MagicMock()
    structured.invoke.return_value = return_exam
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm, structured


# ── Phase 1: schema (additive, backward-compatible) ──
def test_question_defaults_to_open():
    q = Question(question_id="q1", topic="ai", question="What is AI?", correct_answer="x", source_chunk_id="c1")
    assert q.question_type == "open"
    assert q.options is None


def test_question_accepts_mcq_with_options():
    q = Question(question_id="q1", topic="ai", question="Capital of France?", question_type="mcq",
                 options=["Paris", "London", "Rome", "Berlin"], correct_answer="Paris", source_chunk_id="c1")
    assert q.question_type == "mcq"
    assert q.options == ["Paris", "London", "Rome", "Berlin"]


def test_old_exam_json_without_type_loads_as_open():
    data = {
        "session_id": "s1", "topics": ["ai"], "status": "validated",
        "questions": [{"question_id": "q1", "topic": "ai", "question": "?",
                       "correct_answer": "x", "source_chunk_id": "c1"}],
    }
    exam = ExamObject(**data)
    assert exam.questions[0].question_type == "open"


# ── Phase 2: generator ──
@patch("agents.generator_agent._get_llm")
def test_generator_mcq_prompt_requests_four_options(mock_get_llm):
    from agents.generator_agent import generate_exam
    llm, structured = _mock_llm(ExamObject(session_id="s1", topics=["ai"], status="draft", questions=[]))
    mock_get_llm.return_value = llm
    generate_exam(session_id="s1", topics=["ai"], chunks=[_chunk()], num_questions=2, question_type="mcq")
    prompt = structured.invoke.call_args[0][0].lower()
    assert "multiple-choice" in prompt
    assert "options" in prompt
    assert "4" in prompt


@patch("agents.generator_agent._get_llm")
def test_generator_default_open_prompt_has_no_mcq(mock_get_llm):
    from agents.generator_agent import generate_exam
    llm, structured = _mock_llm(ExamObject(session_id="s1", topics=["ai"], status="draft", questions=[]))
    mock_get_llm.return_value = llm
    generate_exam(session_id="s1", topics=["ai"], chunks=[_chunk()], num_questions=2)  # default open
    prompt = structured.invoke.call_args[0][0].lower()
    assert "multiple-choice" not in prompt


@patch("agents.generator_agent._get_llm")
def test_generator_mixed_prompt_asks_for_both(mock_get_llm):
    from agents.generator_agent import generate_exam
    llm, structured = _mock_llm(ExamObject(session_id="s1", topics=["ai"], status="draft", questions=[]))
    mock_get_llm.return_value = llm
    generate_exam(session_id="s1", topics=["ai"], chunks=[_chunk()], num_questions=2, question_type="mixed")
    prompt = structured.invoke.call_args[0][0].lower()
    assert "multiple-choice" in prompt and "open" in prompt


# ── Phase 3: validator (deterministic MCQ structure checks, no LLM) ──
def test_validator_rejects_mcq_when_answer_not_in_options():
    from agents.validator_agent import validate_exam
    exam = ExamObject(session_id="s1", topics=["ai"], status="draft", questions=[
        Question(question_id="q1", topic="ai", question="Capital of France?", question_type="mcq",
                 options=["London", "Rome", "Berlin", "Madrid"], correct_answer="Paris", source_chunk_id="c1")])
    res = validate_exam(exam, [_chunk("c1")])
    assert not res.approved
    assert "q1" in res.rejected_question_ids


def test_validator_rejects_mcq_with_too_few_options():
    from agents.validator_agent import validate_exam
    exam = ExamObject(session_id="s1", topics=["ai"], status="draft", questions=[
        Question(question_id="q1", topic="ai", question="Capital?", question_type="mcq",
                 options=["Paris"], correct_answer="Paris", source_chunk_id="c1")])
    res = validate_exam(exam, [_chunk("c1")])
    assert not res.approved
    assert "q1" in res.rejected_question_ids


# ── Phase 4: corrector (deterministic MCQ grading, no LLM) ──
def test_grade_mcq_correct_match_is_case_insensitive():
    from agents.corrector_agent import _grade_answer
    q = Question(question_id="q1", topic="ai", question="Capital of France?", question_type="mcq",
                 options=["Paris", "London"], correct_answer="Paris", source_chunk_id="c1")
    r = _grade_answer(q, "  paris ", "notes")
    assert r.is_correct is True


def test_grade_mcq_incorrect_names_the_correct_option():
    from agents.corrector_agent import _grade_answer
    q = Question(question_id="q1", topic="ai", question="Capital of France?", question_type="mcq",
                 options=["Paris", "London"], correct_answer="Paris", source_chunk_id="c1")
    r = _grade_answer(q, "London", "notes")
    assert r.is_correct is False
    assert "Paris" in r.explanation


def test_grade_mcq_never_calls_the_llm(monkeypatch):
    from agents import corrector_agent

    def _boom():
        raise AssertionError("LLM must not be called when grading MCQ")

    monkeypatch.setattr(corrector_agent, "_get_llm", _boom)
    q = Question(question_id="q1", topic="ai", question="Capital?", question_type="mcq",
                 options=["A", "B", "C", "D"], correct_answer="A", source_chunk_id="c1")
    r = corrector_agent._grade_answer(q, "A", "notes")
    assert r.is_correct is True


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
