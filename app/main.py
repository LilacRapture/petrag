from fastapi import FastAPI

from .schemas import QueryRequest, QueryResponse

app = FastAPI(title="PetRAG")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """
    TODO (next iteration step):
    1. vector = embed_text(request.question)
    2. hits = vector_store.search(vector, request.top_k, request.project)
    3. answer = llm.generate_answer(request.question, [h.payload["text"] for h in hits])
    4. return QueryResponse(answer=answer, sources=[...])
    """
    raise NotImplementedError
