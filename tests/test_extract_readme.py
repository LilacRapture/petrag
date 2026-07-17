"""
Tests for ingestion/extract_readme.py — the "## "-only splitting logic
and the min-length noise filter (see ADR-004 and ADR-006 in
docs/decisions.md for the reasoning behind both).
"""
from ingestion.extract_readme import _split_by_h2, extract


def test_split_by_h2_separates_sections():
    text = (
        "# Title\n\nIntro paragraph, kept as its own section.\n\n"
        "## First Section\n\nFirst content here that is long enough to pass the filter.\n\n"
        "## Second Section\n\nSecond content here that is also long enough.\n"
    )

    sections = _split_by_h2(text)

    headings = [h for h, _ in sections]
    assert headings == ["", "First Section", "Second Section"]


def test_split_by_h2_ignores_h3_boundaries():
    """
    A "### " line must NOT start a new section — it stays inside the
    enclosing "## " section (see ADR-004: splitting deeper would fragment
    tables/subsections that only make sense together).
    """
    text = (
        "## Parent Section\n\n"
        "Some intro text.\n\n"
        "### Child Subsection\n\n"
        "Content that belongs to the parent.\n"
    )

    sections = _split_by_h2(text)

    assert len(sections) == 1
    heading, body = sections[0]
    assert heading == "Parent Section"
    assert "### Child Subsection" in body


def test_split_by_h2_drops_empty_sections():
    text = "## Empty\n\n## Also Empty\n\n## Has Content\n\nSomething here.\n"

    sections = _split_by_h2(text)

    assert sections == [("Has Content", "Something here.")]


def test_extract_reads_readme_and_docs(tmp_path):
    (tmp_path / "README.md").write_text(
        "# My Project\n\n"
        "## Overview\n\n"
        "This is a long enough overview section to survive the min-length filter.\n"
    )
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "api.md").write_text(
        "## Endpoints\n\n"
        "This section describes the API endpoints in enough detail to pass filtering.\n"
    )

    chunks = list(extract("myproject", str(tmp_path)))

    source_files = {c.source_file for c in chunks}
    assert source_files == {"README.md", "docs/api.md"}
    assert all(c.chunk_type == "doc" for c in chunks)
    assert all(c.project == "myproject" for c in chunks)


def test_extract_skips_sections_below_min_length(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Title\n\n"
        "## Too Short\n\nTiny.\n\n"
        "## Long Enough\n\nThis section has plenty of characters to pass the fifty-char filter.\n"
    )

    chunks = list(extract("myproject", str(tmp_path)))

    headings = {c.extra.get("heading") for c in chunks}
    assert "Too Short" not in headings
    assert "Long Enough" in headings


def test_extract_handles_missing_readme_and_docs(tmp_path):
    """Neither README.md nor docs/ exists — must yield nothing, not raise."""
    chunks = list(extract("myproject", str(tmp_path)))
    assert chunks == []
    