"""
Tests for ingestion/ingest.py::run() — the pipeline orchestration
(extract -> embed -> ensure_collection -> upsert). Extractors and
_chunk_id already have their own unit tests (test_extract_*.py,
test_ingestion_vector_store.py); this only checks run() wires the
pieces together correctly and short-circuits on empty extraction.

Names are patched on the `ingest` module, not on their origin modules
(app.embeddings, ingestion.vector_store) — ingest.py imports them by
name ("from app.embeddings import embed_texts"), so the reference
run() actually calls lives in ingest's own namespace.
"""
from ingestion import ingest
from ingestion.chunking import Chunk


def _fake_chunk(text, chunk_type="doc"):
    return Chunk(text=text, source_file="README.md", chunk_type=chunk_type, project="myproject", extra={})


# ---------------------------------------------------------------------------
# run() — single-source pipeline (extract -> embed -> ensure_collection -> upsert)
# ---------------------------------------------------------------------------


def test_run_short_circuits_on_no_chunks(monkeypatch, caplog):
    caplog.set_level("INFO")
    monkeypatch.setitem(ingest.EXTRACTORS, "readme", lambda project, path: iter([]))

    embed_calls = []
    monkeypatch.setattr(ingest, "embed_texts", lambda texts: embed_calls.append(texts))

    ingest.run("readme", "myproject", "/some/path")

    assert embed_calls == []
    assert "No chunks extracted" in caplog.text


def test_run_embeds_and_upserts_extracted_chunks(monkeypatch):
    chunks = [_fake_chunk("first"), _fake_chunk("second")]
    monkeypatch.setitem(ingest.EXTRACTORS, "readme", lambda project, path: iter(chunks))

    embed_calls = []

    def fake_embed_texts(texts):
        embed_calls.append(texts)
        return [[0.1, 0.2], [0.3, 0.4]]

    monkeypatch.setattr(ingest, "embed_texts", fake_embed_texts)

    fake_client = object()
    monkeypatch.setattr(ingest, "get_client", lambda: fake_client)

    ensure_calls = []
    monkeypatch.setattr(
        ingest, "ensure_collection",
        lambda client, vector_size: ensure_calls.append((client, vector_size)),
    )

    upsert_calls = []
    monkeypatch.setattr(
        ingest, "upsert_chunks",
        lambda client, chunks_arg, vectors: upsert_calls.append((client, chunks_arg, vectors)),
    )

    ingest.run("readme", "myproject", "/some/path")

    assert embed_calls == [["first", "second"]]
    assert ensure_calls == [(fake_client, 2)]  # vector_size must come from len(vectors[0])
    assert upsert_calls == [(fake_client, chunks, [[0.1, 0.2], [0.3, 0.4]])]


def test_run_prints_summary_grouped_by_chunk_type(monkeypatch, caplog):
    caplog.set_level("INFO")
    chunks = [
        _fake_chunk("a", chunk_type="doc"),
        _fake_chunk("b", chunk_type="docstring"),
        _fake_chunk("c", chunk_type="docstring"),
    ]
    monkeypatch.setitem(ingest.EXTRACTORS, "readme", lambda project, path: iter(chunks))
    monkeypatch.setattr(ingest, "embed_texts", lambda texts: [[0.0]] * len(texts))
    monkeypatch.setattr(ingest, "get_client", lambda: object())
    monkeypatch.setattr(ingest, "ensure_collection", lambda client, vector_size: None)
    monkeypatch.setattr(ingest, "upsert_chunks", lambda client, chunks_arg, vectors: None)

    ingest.run("readme", "myproject", "/some/path")

    assert "'doc': 1" in caplog.text
    assert "'docstring': 2" in caplog.text


# ---------------------------------------------------------------------------
# main() — CLI argument handling
# ---------------------------------------------------------------------------


def test_main_with_source_all_runs_every_extractor(monkeypatch):
    calls = []
    monkeypatch.setattr(ingest, "run", lambda source, project, path: calls.append(source))
    monkeypatch.setattr(
        "sys.argv",
        ["ingest.py", "--source", "all", "--project", "myproject", "--path", "/some/path"],
    )

    ingest.main()

    assert calls == sorted(ingest.EXTRACTORS)  # alphabetical: docstrings, git_log, readme
