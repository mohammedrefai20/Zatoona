from typing import TypedDict

from schemas.exam_object import ExamObject, ValidationResult
from schemas.note_chunk import NoteChunk


class ExamState(TypedDict):
    session_id: str
    topics: list[str]
    num_questions: int | None  # None = LLM decides based on content
    difficult: bool
    question_type: str  # "open" | "mcq" | "mixed"
    chunks: list[NoteChunk]
    exam: ExamObject | None
    validation: ValidationResult | None
    iteration: int
    max_iterations: int
