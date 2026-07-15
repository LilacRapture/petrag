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

---

## ADR-007 — AST-based docstring extraction with qualified symbol names

**Date:** Phase 3
**Status:** Accepted

**Decision:** `extract_docstrings.py` walks `.py` files with the `ast`
module, tracking an enclosing-class stack so nested method docstrings get
a qualified `symbol_name` like `"RBACPermission.has_permission"` instead
of a bare `"has_permission"`. Each chunk's text is signature + docstring,
not just the raw docstring string.

**Context:** Many DRF views/serializers implement same-named methods
(`get`, `post`, `create`, `update`) — a bare symbol name would collide
across unrelated classes and lose the "which class" information entirely.

**Alternatives considered:**
- `tokenize`/regex-based extraction — simpler on paper, far more fragile
  against multi-line signatures and decorators
- Skipping nested (method-level) docstrings entirely — would lose most
  of the RBAC-relevant documentation, which lives inside class methods

**Consequences:**
- `_DocstringCollector` deliberately does not descend into function
  bodies — this codebase has no nested function definitions worth
  indexing separately, so recursion stops at the method level

---

## ADR-008 — Exclude venv/site-packages from docstring extraction

**Date:** Phase 3
**Status:** Accepted

**Decision:** `_iter_python_files` skips any path containing
`migrations`, `__pycache__`, `.venv`, `venv`, `site-packages`, or `.git`
in its parts.

**Context:** The first real run against `sources/tasktracker` produced
10219 chunks — two orders of magnitude above the ~50-90 expected. Root
cause: TaskTracker's own `.venv/`, created inside the project root per
its README, was walked recursively along with the application code,
indexing Django/DRF/SimpleJWT and their transitive dependencies.

**Consequences:**
- Re-running after the fix produced 90 chunks across 58 files
- Required one manual `delete_collection` filtered on
  `chunk_type="docstring"` to clear the polluted points before
  re-ingesting — deterministic ids (ADR-005) don't clean up points for
  files that are no longer walked, only overwrite ones that still match

---

## ADR-009 — Batch embeddings, chunked Qdrant upserts, quieted third-party logs

**Date:** Phase 3
**Status:** Accepted

**Decision:**
- `app/embeddings.py` gained `embed_texts()` (batch) alongside
  `embed_text()` (single) — ingestion embeds all chunks in one call
  instead of one `.encode()` per chunk
- `ingestion/vector_store.py`'s `upsert_chunks()` splits points into
  batches of 100 before calling `client.upsert()`, instead of one HTTP
  PUT for the entire set
- `ingest.py`'s `main()` sets `logging.getLogger("httpx").setLevel(WARNING)`
  after enabling `INFO`-level `basicConfig`

**Context:** The first (pre-fix, ~10k-chunk) docstrings run surfaced
three real problems: one `.encode()` call per chunk flooded the terminal
with a tqdm progress bar per call; upserting all points in a single PUT
sent an 87MB JSON payload, exceeding Qdrant's default 32MB request size
limit (`400 Bad Request`); and `httpx`'s own `INFO`-level request logging
got pulled in as a side effect of adding `basicConfig(level=INFO)` for
our own skip-diagnostics.

**Consequences:**
- Batching is also meaningfully faster — one model forward pass over
  many texts instead of many individual calls
- Batch size (100) is a fixed constant, not derived from payload size —
  fine at current corpus size; would need a smarter split if individual
  chunk texts grow much larger

---

## ADR-010 — git log parsing via non-printable field/record separators

**Date:** Phase 4
**Status:** Accepted

**Decision:** `extract_git_log.py` runs
`git log --pretty=format:"\x1e%H\x1f%ai\x1f%s" --name-only` and parses
output by splitting on `\x1e` (record separator) / `\x1f` (unit
separator), instead of parsing git's normal human-readable log format
with regex.

**Context:** Commit subjects and file paths can contain almost any
character, including ones that would be ambiguous delimiters (colons,
dashes, pipes). `\x1e`/`\x1f` are ASCII control characters that don't
appear in normal git log content, making `split()` reliable without a
parsing library.

**Alternatives considered:**
- Parsing default `git log` output — fragile across multi-line commit
  messages
- A dedicated git-log-to-JSON tool — extra dependency for something
  git's own format strings already solve

**Consequences:**
- Only the commit subject (`%s`) is captured, not the full body (`%b`)
  — TaskTracker's commits are conventional-commit-style one-liners in
  practice, so nothing has been lost so far; revisit if that changes
- Merge commits' file lists would come back empty under this invocation
  (`--name-only` doesn't show a diff for merges without `-m`/`--first-parent`)
  — not currently relevant since the repo's history is linear
- Extraction is wrapped in `try/except` around `subprocess.run`, so a
  missing `.git` directory degrades to zero commit chunks + a warning
  log, rather than crashing the whole ingest run for other sources