from pydantic import BaseModel, ConfigDict


class NoteChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    topic: str
    content: str
    session_id: str
