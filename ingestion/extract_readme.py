"""
Reads README.md and every docs/*.md file under the project checkout,
splits each by level-2 markdown headers ("## "), and yields one Chunk
per section.

Design choice: only split on "## ", not "###"+. A level-1 header is
usually just the doc title (nothing worth searching on its own — its
content becomes the untitled intro chunk). Splitting on "###" would
fragment sections that only make sense together — e.g. in
docs/rbac-schema.md, the "## AccessRules per Role" section has several
role tables that are meaningless without the surrounding "## " context.
"""
from collections.abc import Iterator
from pathlib import Path

from .chunking import Chunk

_H2_PREFIX = "## "


def _split_by_h2(text: str) -> list[tuple[str, str]]:
    """
    Split markdown text into (heading, body) pairs on "## " lines.
    Content before the first "## " (h1 title + intro paragraph) becomes
    its own section with heading="" — intros often explain the doc's
    purpose and are worth keeping as a chunk.
    """
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith(_H2_PREFIX):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line[len(_H2_PREFIX):].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    # drop sections that are just whitespace (e.g. a header immediately
    # followed by another header)
    return [(h, b) for h, b in sections if b]


def _iter_markdown_files(source_path: str) -> Iterator[Path]:
    root = Path(source_path)

    readme = root / "README.md"
    if readme.exists():
        yield readme

    docs_dir = root / "docs"
    if docs_dir.exists():
        yield from sorted(docs_dir.glob("*.md"))


def extract(project: str, source_path: str) -> Iterator[Chunk]:
    for md_file in _iter_markdown_files(source_path):
        text = md_file.read_text(encoding="utf-8")
        relative_path = str(md_file.relative_to(source_path))

        for heading, body in _split_by_h2(text):
            # TODO: filter out near-empty chunks (e.g. architecture.md's
            # intro section is just the h1 title, ~30 chars, no real
            # content). Observed polluting top-5 retrieval results with a
            # near-zero-information match — add a min length threshold
            # (something like len(body) < 50) and skip/merge such sections
            # instead of indexing them as-is.
            chunk_text = f"{heading}\n\n{body}" if heading else body
            yield Chunk(
                text=chunk_text,
                source_file=relative_path,
                chunk_type="doc",
                project=project,
                extra={"heading": heading} if heading else {},
            )
