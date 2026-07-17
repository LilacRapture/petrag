# PetRAG

RAG search over pet projects using
Qdrant + local embeddings (sentence-transformers) + a local LLM (Ollama).

## Architecture

Two independent processes:

- `ingestion/` — batch pipeline: reads source checkouts, chunks them,
  computes embeddings, writes to Qdrant. Run manually when source data
  changes.
- `app/` — FastAPI service: takes a question, searches Qdrant, generates
  an answer via Ollama. Runs continuously.

## Stack

- Python 3.12, FastAPI
- Qdrant (vector database)
- sentence-transformers (`all-MiniLM-L6-v2`) — embeddings, fully local
- Ollama (`qwen2.5-coder`) — answer generation, fully local
- Docker + OrbStack (Qdrant runs in a container; Ollama runs natively on
  the host — see `docs/decisions.md` ADR-002)

## Quick start (full stack)

1. Install the Ollama model: `ollama pull qwen2.5-coder:7b`
2. `cp .env.example .env`
3. Symlink (not copy) each project checkout you want indexed into `sources/`:
```bash
   ln -s /full/path/to/tasktracker sources/tasktracker
   ln -s /full/path/to/dnd_backend sources/dnd_backend
   ln -s /full/path/to/fairytale sources/fairytale
```
4. `docker compose up --build`
5. Check it's up: `http :8001/health`

## Development (local, without rebuilding the image)

For iterating on `ingestion/`/`app/` it's faster to run code directly
from a venv instead of waiting on `docker compose build` after every
change:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env.local` (gitignored, never committed) with host-specific
overrides — these take precedence over `.env` for local runs:

```bash
# .env.local
QDRANT_HOST=localhost
SOURCE_PROJECT_PATH=sources/tasktracker
OLLAMA_BASE_URL=http://localhost:11434
```

Then:

```bash
docker compose up -d qdrant          # Qdrant always runs in Docker
python -m ingestion.ingest --source readme --project tasktracker       # or docstrings / git_log
uvicorn app.main:app --reload --port 8000
http POST :8000/query question="..." project=tasktracker top_k:=5
```

Linter: `ruff check .` (config in `pyproject.toml`).

## Testing

```bash
pytest tests/ -v
```

CI runs `ruff check` + the full test suite (with coverage) on every
push — see `.github/workflows/tests.yml`.

## Documentation

| File | Purpose |
|------|---------|
| [AGENTS.md](AGENTS.md) | Project conventions, phase status |
| [docs/decisions.md](docs/decisions.md) | ADR (architecture decisions) |

## Status

**Phases 1-5 complete** — the end-to-end pipeline works: README/docs +
docstrings + git log are indexed into Qdrant, and `/query` answers via
retrieval + a local LLM. TaskTracker, DnD Backend, and Fairytale are all
indexed into a single shared Qdrant collection, isolated by a `project`
field in each point's payload (see ADR-011). Chunking, ingestion, and
per-project filtering have all been verified against all three sources.

**Next:** waiting for other projects of larger complexity to become
available to stress-test the pipeline further.

### Ideas for future work

- **Incremental re-indexing** — `ingest.py` currently re-extracts and
  re-embeds every chunk on every run, even unchanged ones. Deterministic
  IDs (ADR-005) prevent duplicate points, but not redundant embedding
  work. Comparing a content hash against the existing Qdrant payload
  before embedding would make re-runs cheaper as the corpus grows.
- **Upsert batch size** — `_UPSERT_BATCH_SIZE = 100` (ADR-009) is a fixed
  constant, not derived from actual payload size. Revisit if a future
  project's chunks are much larger.
- **Non-Python extractors** — `extract_docstrings.py` is Python/`ast`-only.
  A project in another language would need a new extractor.
- **Min-length filtering consistency** — `extract_readme.py` filters out
  near-empty sections (ADR-006); `extract_docstrings.py` does not. Worth
  a consistent policy if trivial one-line docstrings start polluting
  retrieval results.

Detailed phase-by-phase status lives in [AGENTS.md](AGENTS.md).