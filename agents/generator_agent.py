from langchain_ollama import ChatOllama

from config.settings import MODEL_NAME, OLLAMA_BASE_URL
from schemas.exam_object import ExamObject, Question
from schemas.note_chunk import NoteChunk


def _get_llm() -> ChatOllama:
    return ChatOllama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0.3)


def _format_chunks(chunks: list[NoteChunk]) -> str:
    return "\n\n".join(
        f"[{chunk.chunk_id}] (topic: {chunk.topic})\n{chunk.content}"
        for chunk in chunks
    )


def _format_existing_questions(questions: list[Question]) -> str:
    if not questions:
        return "None"
    return "\n".join(
        f"- {q.question_id}: {q.question} (source: {q.source_chunk_id})"
        for q in questions
    )


def generate_exam(
    session_id: str,
    topics: list[str],
    chunks: list[NoteChunk],
    existing_exam: ExamObject | None = None,
    retry_feedback: str | None = None,
    rejected_question_ids: list[str] | None = None,
) -> ExamObject:
    """Generate exam questions from note chunks. LLM decides question count."""
    llm = _get_llm()
    structured_llm = llm.with_structured_output(ExamObject)

    keep_questions: list[Question] = []
    if existing_exam and rejected_question_ids:
        rejected_ids = set(rejected_question_ids)
        keep_questions = [
            q for q in existing_exam.questions if q.question_id not in rejected_ids
        ]

    prompt = f"""You are an exam generator for a classroom assistant.

Create exam questions ONLY from the provided note chunks.
Session ID: {session_id}
Topics: {", ".join(topics)}

Note chunks:
{_format_chunks(chunks)}

Rules:
1. Decide how many questions to create based on chunk content richness.
   Create roughly one question per substantive chunk; skip empty or redundant chunks.
2. Every question MUST use a real source_chunk_id from the chunks above.
3. Each question must belong to one of the requested topics.
4. correct_answer must be directly supported by the source chunk content.
5. Set status to "draft".
6. Use unique question_id values (e.g. q-001, q-002).
"""

    if keep_questions:
        prompt += f"""
This is a retry. Keep these already-approved questions unchanged:
{_format_existing_questions(keep_questions)}

Validator feedback on rejected questions:
{retry_feedback}

Replace only the rejected questions. Include the kept questions in the final output.
"""

    result: ExamObject = structured_llm.invoke(prompt)

    return ExamObject(
        session_id=session_id,
        topics=topics,
        status="draft",
        questions=result.questions,
    )
