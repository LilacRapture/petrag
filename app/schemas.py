from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    project: str | None = None   # optional filter, e.g. "tasktracker"
    top_k: int = 5


class RetrievedChunk(BaseModel):
    text: str
    source_file: str
    chunk_type: str   # "doc" | "docstring" | "commit"
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[RetrievedChunk]
