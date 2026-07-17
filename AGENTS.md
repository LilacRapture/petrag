# AGENTS.md — PetRAG

> RAG search over pet projects (TaskTracker, DnD Backend, Fairytale),
> using Qdrant + local embeddings (sentence-transformers) + local LLM
> (Ollama). Learning-focused: understand RAG/vector DB internals by
> building them, not by using a framework that hides the pieces.

## Architecture

Two independent processes — see docs/decisions.md for why:

- `ingestion/` — batch pipeline (extract → chunk → embed → upsert into
  Qdrant). Run manually when source data changes.
- `app/` — FastAPI service (embed question → search Qdrant → generate
  answer via Ollama). Runs continuously.

## Rules

- Ollama runs on the HOST (Metal acceleration), never in docker-compose (ADR-002)
- Chunking finds semantically complete units — never fixed-character splitting
- Chunk ids are deterministic (ADR-005) — re-ingestion must stay idempotent
- No `print()` for debugging — use `logging`
- Non-obvious decisions get an ADR in docs/decisions.md

## Status

### Phase 1 — Done
- [x] extract_readme.py + chunking + ingest.py (README/docs → Qdrant)
- [x] Deterministic chunk ids, min-length filter, logging

### Phase 2 — Done
- [x] app/vector_store.py (search) + app/llm.py + app/main.py → working /query

### Phase 3 — Done
- [x] extract_docstrings.py (ast-based, qualified symbol names)
- [x] Batch embeddings, chunked upserts, quieted httpx logging

### Phase 4 — Done
- [x] extract_git_log.py (control-character-delimited git log parsing)

### Phase 5 — Done
- [x] Second/third project (DnD Backend, Fairytale) — single Qdrant
      collection with `project` payload filter