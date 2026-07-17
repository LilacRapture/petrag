import logging

from fastapi import FastAPI, HTTPException
from httpx import ConnectError, HTTPStatusError, TimeoutException
from qdrant_client.http.exceptions import ApiException

from .config import settings
from .embeddings import embed_text
from .llm import generate_answer
from .schemas import QueryRequest, QueryResponse, RetrievedChunk
from .vector_store import search

logger = logging.getLogger(__name__)

app = FastAPI(title="PetRAG")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    query_vector = embed_text(request.question)

    try:
        hits = search(query_vector, top_k=request.top_k, project=request.project)
    except (ConnectError, TimeoutException, ApiException) as exc:
        logger.error("Qdrant search failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Vector store is unavailable. Is Qdrant running (docker compose up qdrant)?",
        ) from exc

    if not hits:
        return QueryResponse(
            answer="No relevant information found in the indexed projects.",
            sources=[],
        )

    context_chunks = [hit.payload["text"] for hit in hits]
    project_label = request.project or settings.source_project_name

    try:
        answer = generate_answer(request.question, context_chunks, project_label)
    except ConnectError as exc:
        logger.error("Ollama connection failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="LLM backend is unavailable. Is Ollama running on the host?",
        ) from exc
    except TimeoutException as exc:
        logger.error("Ollama request timed out: %s", exc)
        raise HTTPException(
            status_code=504,
            detail="LLM backend timed out generating a response.",
        ) from exc
    except HTTPStatusError as exc:
        logger.error("Ollama returned an error status: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="LLM backend returned an unexpected error.",
        ) from exc

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
    