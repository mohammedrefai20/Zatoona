from langchain_openai import ChatOpenAI

from config.settings import MODEL_NAME, BASE_URL, LIGHTNING_API_KEY
from schemas.exam_object import ExamObject, Question
from schemas.note_chunk import NoteChunk


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=MODEL_NAME,
        base_url=BASE_URL,
        api_key=LIGHTNING_API_KEY,
        temperature=0.3,
    )


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


def _build_quantity_instruction(
    num_questions: int | None,
    num_chunks: int,
    is_retry: bool,
    num_to_replace: int,
) -> str:
    """Build the instruction that tells the LLM how many questions to generate."""
    if is_retry:
        return (
            f"Generate exactly {num_to_replace} replacement question(s) "
            f"to replace the rejected ones."
        )

    if num_questions is not None:
        cap = min(num_questions, num_chunks)
        if cap < num_questions:
            return (
                f"The user requested {num_questions} questions, but only "
                f"{num_chunks} substantive chunk(s) are available. "
                f"Generate {cap} question(s) — one per chunk — which is "
                f"the maximum possible from the provided material."
            )
        return f"Generate exactly {num_questions} question(s) as requested by the user."

    # No specific count requested — LLM decides
    return (
        "Decide how many questions to create based on chunk content richness. "
        "Create roughly one question per substantive chunk; "
        "skip empty or redundant chunks."
    )


def generate_exam(
    session_id: str,
    topics: list[str],
    chunks: list[NoteChunk],
    num_questions: int | None = None,
    difficult: bool = False,
    existing_exam: ExamObject | None = None,
    retry_feedback: str | None = None,
    rejected_question_ids: list[str] | None = None,
) -> ExamObject:
    """Generate exam questions from note chunks.

    Args:
        num_questions: Desired number of questions. None lets the LLM decide.
                       If the number exceeds available chunks, the generator
                       produces the maximum it can.
    """
    llm = _get_llm()
    structured_llm = llm.with_structured_output(ExamObject)

    keep_questions: list[Question] = []
    is_retry = bool(existing_exam and rejected_question_ids)
    if is_retry:
        rejected_ids = set(rejected_question_ids)
        keep_questions = [
            q for q in existing_exam.questions if q.question_id not in rejected_ids
        ]

    quantity_instruction = _build_quantity_instruction(
        num_questions=num_questions,
        num_chunks=len(chunks),
        is_retry=is_retry,
        num_to_replace=len(rejected_question_ids) if rejected_question_ids else 0,
    )

    if difficult:
        difficulty_instruction = (
            "Each question MUST combine and synthesize information from MULTIPLE note chunks (at least 2) to test complex connections.\n"
            "   Identify all the chunks used and list their IDs separated by commas in the `source_chunk_id` field (e.g. 'chunk-001, chunk-002')."
        )
    else:
        difficulty_instruction = (
            "Each question MUST test information from EXACTLY ONE note chunk.\n"
            "   List its single ID in the `source_chunk_id` field (e.g. 'chunk-001')."
        )

    available_ids = ", ".join(c.chunk_id for c in chunks)

    prompt = f"""You are an exam generator for a classroom assistant.

Your task is to create high-quality exam questions ONLY from the provided note chunks.

Session ID: {session_id}
Topics: {", ".join(topics)}

=== NOTE CHUNKS (source material) ===
{_format_chunks(chunks)}

=== AVAILABLE source_chunk_id VALUES ===
{available_ids}

=== QUESTION COUNT ===
{quantity_instruction}

=== RULES ===
1. Every question MUST reference real source_chunk_id value(s) from the list above.
   Do NOT invent or modify chunk IDs.
2. Each question must belong to one of the requested topics: {", ".join(topics)}.
3. {difficulty_instruction}
4. The correct_answer MUST be directly and fully supported by the content
   of the referenced source chunk(s). Do NOT add external knowledge.
5. Set status to "draft".
6. Use unique, sequential question_id values (e.g. q-001, q-002, q-003).
7. Each question should test a distinct concept — avoid asking the same
   thing in different words.
"""

    if is_retry:
        prompt += f"""
=== RETRY INSTRUCTIONS ===
The following questions were already approved and must NOT be regenerated.
Do NOT include them in your output — they will be merged automatically.

Already-approved questions (DO NOT reproduce these):
{_format_existing_questions(keep_questions)}

Validator feedback on rejected questions:
{retry_feedback}

Generate ONLY the replacement questions. Fix the issues described in the
feedback. Use new question_id values that don't conflict with the kept ones.
"""

    result: ExamObject = structured_llm.invoke(prompt)

    # --- Post-processing: merge approved questions with newly generated ones ---
    if is_retry and keep_questions:
        # Programmatically merge instead of trusting the LLM to include them
        kept_ids = {q.question_id for q in keep_questions}
        new_questions = [
            q for q in result.questions if q.question_id not in kept_ids
        ]
        final_questions = keep_questions + new_questions
    else:
        final_questions = result.questions

    return ExamObject(
        session_id=session_id,
        topics=topics,
        status="draft",
        questions=final_questions,
    )

