from typing import Literal

from pydantic import BaseModel


class Question(BaseModel):
    question_id: str
    topic: str
    question: str
    correct_answer: str
    source_chunk_id: str


class ExamObject(BaseModel):
    session_id: str
    topics: list[str]
    status: Literal["draft", "validated"]
    questions: list[Question]


class ValidationResult(BaseModel):
    approved: bool
    rejected_question_ids: list[str]
    feedback: str
