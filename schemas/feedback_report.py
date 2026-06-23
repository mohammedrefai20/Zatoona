from pydantic import BaseModel

class QuestionResult(BaseModel):
    question_id    : str
    question       : str
    student_answer : str
    is_correct     : bool
    explanation    : str
    source_chunk   : str

class FeedbackReport(BaseModel):
    session_id       : str
    score            : int
    topics_to_review : list[str]
    encouragement    : str
    results          : list[QuestionResult]