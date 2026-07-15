# Architecture Decision Records (ADR) — PetRAG

## ADR-001 — Local-only embeddings and LLM (no external API)

**Date:** project start
**Status:** Accepted

**Decision:** Use sentence-transformers (all-MiniLM-L6-v2) for embeddings
and a local Ollama model (qwen2.5-coder) for answer generation. No OpenAI
or other paid API.

**Context:** Learning-focused project; zero marginal cost per query/index
run matters more than best-possible answer quality at this stage.

**Alternatives considered:**
- OpenAI embeddings + GPT — simplest, higher quality, but not free
- Hybrid (local embeddings + paid LLM only for generation) — considered,
  rejected for now to keep the stack fully self-contained

**Consequences:**
- Answer quality is bounded by local model size/quality
- No API key management, no usage-based billing to track

---

## ADR-002 — Ollama runs natively on host, not in docker-compose

**Date:** project start
**Status:** Accepted

**Decision:** Ollama is NOT a docker-compose service. It runs natively on
macOS; the `api` container reaches it via `http://host.docker.internal:11434`.

**Context:** Docker on macOS (Docker Desktop and OrbStack alike) does not
pass through GPU/Metal acceleration to containers. Containerizing Ollama
would force CPU-only inference, losing Apple Silicon acceleration for no
benefit — reproducibility doesn't require it since Ollama isn't part of
the app's own code, just an external dependency.

**Consequences:**
- `OLLAMA_BASE_URL` differs between container runs (`host.docker.internal`)
  and local venv runs (`localhost`) — handled via `.env` / `.env.local`
- Whoever runs this project needs Ollama installed and the model pulled
  separately — not fully containerized, documented in README

---

## ADR-003 — FastAPI + own docker-compose, not a Django app inside TaskTracker

**Date:** project start
**Status:** Accepted

**Decision:** PetRAG is a standalone service/repo with its own
docker-compose (Qdrant + api), not a new Django app added to TaskTracker.

**Context:** Portfolio goal is demonstrating range across projects
(different frameworks, different concerns) rather than accumulating
everything into one codebase. RAG/vector search is also a genuinely
separate concern from TaskTracker's CRUD+RBAC domain.

**Consequences:**
- Two docker-compose stacks to run when cross-referencing TaskTracker
  source during ingestion (TaskTracker itself isn't run — only its
  checkout is read from disk, read-only, via bind mount)

---

## ADR-004 — Markdown chunking splits only on "## " headers

**Date:** Phase 1
**Status:** Accepted

**Decision:** `extract_readme.py` splits markdown files on level-2
headers only. Deeper headers (`###`+) stay inside their parent chunk.

**Context:** A level-1 header is just the doc title. Splitting on `###`
would fragment sections that only make sense together — e.g. in
docs/rbac-schema.md, "## Two-layer enforcement" has several `###`
subsections that are meaningless in isolation.

**Consequences:**
- Some chunks are fairly long (a full "## " section with all its
  subsections) — acceptable for the embedding model's context window
  at this corpus size; revisit if chunks start exceeding useful length

---

## ADR-005 — Deterministic chunk ids (uuid5) instead of random uuid4

**Date:** Phase 1
**Status:** Accepted

**Decision:** `ingestion/vector_store.py` derives each point's Qdrant id
from `uuid5(NAMESPACE_URL, f"{project}:{chunk_type}:{source_file}:{extra}")`
instead of a random `uuid4()`.

**Context:** Random ids meant re-running ingestion on unchanged files
created duplicate points instead of updating existing ones — discovered
after a few manual re-runs during Phase 1/2 testing.

**Consequences:**
- Re-running ingestion is now idempotent for unchanged sections
- The natural key deliberately excludes `chunk.text` — editing a
  section's content updates the same point rather than creating a new one
- Collection needed a one-time `delete_collection` + full re-ingest to
  clear pre-existing duplicate points from the old id scheme

---

## ADR-006 — Minimum chunk length filter for markdown sections

**Date:** Phase 1
**Status:** Accepted

**Decision:** Sections shorter than 50 characters (after stripping) are
skipped entirely, not indexed and not merged into neighboring sections.

**Context:** Near-empty sections (e.g. architecture.md's intro is just
the h1 title, docs/decisions.md's "Template for new ADRs" section) were
observed occupying top-5 retrieval slots with near-zero information.

**Alternatives considered:**
- Merge into the next/previous section instead of dropping — rejected
  for markdown docs, where these are genuinely empty/decorative, not
  lossy truncation of real content. May revisit for extract_docstrings.py,
  where short-but-real docstrings are a different case.

**Consequences:**
- ~2-4 near-empty sections dropped from the corpus per ingestion run
- Skipped sections are logged at INFO level for visibility