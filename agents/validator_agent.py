from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config.settings import MODEL_NAME, BASE_URL, LIGHTNING_API_KEY
from schemas.exam_object import ExamObject, ValidationResult
from schemas.note_chunk import NoteChunk


class _QuestionValidation(BaseModel):
    question_id: str
    approved: bool
    reason: str


class _ValidationResponse(BaseModel):
    results: list[_QuestionValidation]


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=MODEL_NAME,
        base_url=BASE_URL,
        api_key=LIGHTNING_API_KEY,
        temperature=0,
    )


def _format_chunks(chunks: list[NoteChunk]) -> str:
    chunk_map = {c.chunk_id: c for c in chunks}
    return "\n\n".join(
        f"[{cid}] (topic: {chunk_map[cid].topic})\n{chunk_map[cid].content}"
        for cid in chunk_map
    )


def validate_exam(exam: ExamObject, chunks: list[NoteChunk]) -> ValidationResult:
    """Validate each question against its source chunk."""
    chunk_ids = {c.chunk_id for c in chunks}

    rejected_ids: list[str] = []
    feedback_lines: list[str] = []

    for question in exam.questions:
        source_ids = [cid.strip() for cid in question.source_chunk_id.split(",") if cid.strip()]
        if not source_ids or not all(sid in chunk_ids for sid in source_ids):
            rejected_ids.append(question.question_id)
            feedback_lines.append(
                f"REJECTED: {question.question_id}: "
                f"source_chunk_id '{question.source_chunk_id}' contains invalid or missing chunk ID(s)."
            )

    questions_to_llm_check = [
        q for q in exam.questions if q.question_id not in rejected_ids
    ]

    if questions_to_llm_check:
        llm = _get_llm()
        structured_llm = llm.with_structured_output(_ValidationResponse)

        questions_text = "\n".join(
            f"- {q.question_id} (source: {q.source_chunk_id}, topic: {q.topic})\n"
            f"  Q: {q.question}\n"
            f"  A: {q.correct_answer}"
            for q in questions_to_llm_check
        )

        prompt = f"""You are an exam validator. Check each question against its source chunk(s).

Source chunks:
{_format_chunks(chunks)}

Questions to validate:
{questions_text}

For each question:
1. Verify the correct_answer is directly supported by the content of the referenced source chunk(s) listed in source_chunk_id.
2. Verify the question is answerable from those chunk(s) alone.
3. If the question is valid, set approved=true and provide a brief confirmation in the reason field.
4. If the question is invalid (wrong, unsupported, hallucinated, or references an incorrect source chunk), set approved=false.
5. For rejected questions, you MUST provide detailed, constructive, and highly actionable feedback in the reason field. Explain exactly what is wrong (e.g. what specific facts were hallucinated or unsupported by the referenced note chunk) and give concrete instructions on how the generator can rewrite it to be fully grounded in the source chunk(s).
"""

        response: _ValidationResponse = structured_llm.invoke(prompt)

        for result in response.results:
            if not result.approved:
                rejected_ids.append(result.question_id)
                feedback_lines.append(
                    f"REJECTED: {result.question_id}: {result.reason}"
                )

    approved = len(rejected_ids) == 0
    feedback = "\n".join(feedback_lines) if feedback_lines else "All questions approved."

    return ValidationResult(
        approved=approved,
        rejected_question_ids=rejected_ids,
        feedback=feedback,
    )
