"""
Tests for ingestion/vector_store.py's _chunk_id — the deterministic
uuid5 scheme from ADR-005, which replaced random uuid4 specifically to
fix duplicate points on re-ingestion.
"""
from ingestion.chunking import Chunk
from ingestion.vector_store import _chunk_id


def _chunk(text="some text", **extra):
    return Chunk(
        text=text,
        source_file="README.md",
        chunk_type="doc",
        project="myproject",
        extra=extra,
    )


def test_chunk_id_is_deterministic_across_calls():
    chunk = _chunk(heading="Overview")
    assert _chunk_id(chunk) == _chunk_id(chunk)


def test_chunk_id_ignores_text_changes():
    """
    Core guarantee from ADR-005: editing a section's content must
    update the same Qdrant point, not create a new one.
    """
    original = _chunk(text="Original content.", heading="Overview")
    edited = _chunk(text="Completely different content now.", heading="Overview")

    assert _chunk_id(original) == _chunk_id(edited)


def test_chunk_id_differs_by_source_file():
    a = _chunk(heading="Overview")
    b = Chunk(text="some text", source_file="OTHER.md", chunk_type="doc", project="myproject", extra={"heading": "Overview"})

    assert _chunk_id(a) != _chunk_id(b)


def test_chunk_id_differs_by_extra_fields():
    """
    This is what actually disambiguates two docstring chunks from the
    same file — e.g. two functions both documented in sample.py.
    """
    a = _chunk(symbol_name="foo")
    b = _chunk(symbol_name="bar")

    assert _chunk_id(a) != _chunk_id(b)


def test_chunk_id_differs_by_project():
    a = _chunk(heading="Overview")
    b = Chunk(text="some text", source_file="README.md", chunk_type="doc", project="other_project", extra={"heading": "Overview"})

    assert _chunk_id(a) != _chunk_id(b)
    