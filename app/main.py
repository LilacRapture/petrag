from fastapi import FastAPI

from .config import settings
from .embeddings import embed_text
from .llm import generate_answer
from .schemas import QueryRequest, QueryResponse, RetrievedChunk
from .vector_store import search

app = FastAPI(title="PetRAG")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    query_vector = embed_text(request.question)
    hits = search(query_vector, top_k=request.top_k, project=request.project)

    if not hits:
        return QueryResponse(
            answer="No relevant information found in the indexed projects.",
            sources=[],
        )

    context_chunks = [hit.payload["text"] for hit in hits]
    project_label = request.project or settings.source_project_name
    answer = generate_answer(request.question, context_chunks, project_label)

    sources = [
        RetrievedChunk(
            text=hit.payload["text"],
            source_file=hit.payload["source_file"],
            chunk_type=hit.payload["chunk_type"],
            score=hit.score,
        )
        for hit in hits
    ]
    return QueryResponse(answer=answer, sources=sources)
    