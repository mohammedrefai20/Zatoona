from langchain_ollama import ChatOllama
from pydantic import BaseModel

from config.settings import MODEL_NAME, OLLAMA_BASE_URL
from schemas.exam_object import ExamObject, ValidationResult
from schemas.note_chunk import NoteChunk


class _QuestionValidation(BaseModel):
    question_id: str
    approved: bool
    reason: str


class _ValidationResponse(BaseModel):
    results: list[_QuestionValidation]


def _get_llm() -> ChatOllama:
    return ChatOllama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0)


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
        if question.source_chunk_id not in chunk_ids:
            rejected_ids.append(question.question_id)
            feedback_lines.append(
                f"REJECTED: {question.question_id}: "
                f"source_chunk_id '{question.source_chunk_id}' not found in available chunks."
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

        prompt = f"""You are an exam validator. Check each question against its source chunk.

Source chunks:
{_format_chunks(chunks)}

Questions to validate:
{questions_text}

For each question:
1. Verify the correct_answer is directly supported by the source chunk content.
2. Verify the question is answerable from that chunk alone.
3. Mark approved=false if the answer is wrong, unsupported, or hallucinated.
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
