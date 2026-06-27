import json
from pathlib import Path
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from schemas.exam_object import ExamObject, Question
from schemas.feedback_report import FeedbackReport, QuestionResult
from config.settings import GROQ_API_KEY, GROQ_MODEL
from mcp_server.mcp_client import get_chunk_by_id

# ── LLM setup ───────────────────────────────────────────────
def _get_llm():
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model_name=GROQ_MODEL
    )

# ── helpers ─────────────────────────────────────────────────

def _load_json(path: str) -> dict:
    with open(Path(path)) as f:
        return json.load(f)


def _chunk_content_for_question(source_chunk_id: str, session_id: str | None) -> str:
    chunk_ids = [cid.strip() for cid in source_chunk_id.split(",") if cid.strip()]
    parts = []
    for chunk_id in chunk_ids:
        chunk = get_chunk_by_id(chunk_id, session_id=session_id)
        if chunk:
            parts.append(chunk.content)
    return "\n\n".join(parts) if parts else "no notes available for this topic"

def _grade_answer(
    question: Question,
    student_answer: str,
    chunk_content: str
) -> QuestionResult:
    # Multiple-choice is graded deterministically — no LLM, no variance, instant.
    if getattr(question, "question_type", "open") == "mcq":
        correct = (question.correct_answer or "").strip().casefold()
        chosen = (student_answer or "").strip().casefold()
        is_correct = bool(chosen) and chosen == correct
        explanation = (
            "Correct." if is_correct
            else f"The correct answer is: {question.correct_answer}."
        )
        return QuestionResult(
            question_id=question.question_id,
            question=question.question,
            student_answer=student_answer,
            is_correct=is_correct,
            explanation=explanation,
            source_chunk=chunk_content,
        )

    # sends one (open-ended) question to the LLM and gets back structured feedback

    system_prompt = """
    You are an exam corrector agent. 
    Your job is to grade a student answer and give clear helpful feedback.
    Always respond in this exact JSON format with no extra text:
    {
      "is_correct": true or false,
      "explanation": "your explanation here"
    }
    """

    user_prompt = f"""
    Question: {question.question}
    Correct answer: {question.correct_answer}
    Student answer: {student_answer}
    Relevant notes: {chunk_content}

    Grade the student answer.
    If wrong, explain what the correct answer is and reference the notes.
    If correct, give a short confirmation.
    """

    response = _get_llm().invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])

    # parse the LLM JSON response
    result = json.loads(response.content)

    return QuestionResult(
        question_id    = question.question_id,
        question       = question.question,
        student_answer = student_answer,
        is_correct     = result["is_correct"],
        explanation    = result["explanation"],
        source_chunk   = chunk_content
    )

def _generate_encouragement(score: int, total: int, topics_to_review: list[str]) -> str:
    # generates a personalized encouragement message based on the score

    user_prompt = f"""
    A student scored {score} out of {total} on a history exam.
    The topics they need to review are: {', '.join(topics_to_review) if topics_to_review else 'none'}.
    Write a short encouraging message (3 sentences max) that motivates them to keep studying.
    Be warm and positive.
    """

    response = _get_llm().invoke([HumanMessage(content=user_prompt)])
    return response.content.strip()

# ── main corrector function ──────────────────────────────────
def run_corrector(
    exam_path: str       = None,
    answers_path: str    = None,
    exam: ExamObject     = None,
    answers: dict        = None,
    session_id: str      = None,
    topics: list[str]    = None
) -> FeedbackReport:

    # accept either a preloaded object or load from file
    if exam is None:
        from agents.exam_loader import load_exam
        exam = load_exam(session_id=session_id, topics=topics) if exam_path is None else ExamObject(**_load_json(exam_path))
    if answers is None:
        from agents.answer_loader import load_answers
        answers = load_answers() if answers_path is None else _load_json(answers_path)

    lookup_session_id = session_id or exam.session_id
    answer_map = {a["question_id"]: a["student_answer"] for a in answers["answers"]}

    results = []
    topics_to_review = []

    for question in exam.questions:
        student_answer = answer_map.get(question.question_id, "")
        chunk_content = _chunk_content_for_question(
            question.source_chunk_id,
            lookup_session_id,
        )

        # grade the answer
        result = _grade_answer(question, student_answer, chunk_content)
        results.append(result)

        # collect topics where student was wrong
        if not result.is_correct and question.topic not in topics_to_review:
            topics_to_review.append(question.topic)

    score         = sum(1 for r in results if r.is_correct)
    encouragement = _generate_encouragement(score, len(results), topics_to_review)

    return FeedbackReport(
        session_id       = exam.session_id,
        score            = score,
        topics_to_review = topics_to_review,
        encouragement    = encouragement,
        results          = results
    )