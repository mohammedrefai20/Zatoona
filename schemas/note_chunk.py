from pydantic import BaseModel

class NoteChunk(BaseModel):
    chunk_id   : str
    topic      : str
    content    : str
    session_id : str