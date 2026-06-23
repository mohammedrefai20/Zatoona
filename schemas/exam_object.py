from pydantic import BaseModel

class Question(BaseModel):
    question_id     : str
    topic           : str
    question        : str
    correct_answer  : str
    source_chunk_id : str

class ExamObject(BaseModel):
    session_id : str
    topics     : list[str]
    status     : str
    questions  : list[Question]