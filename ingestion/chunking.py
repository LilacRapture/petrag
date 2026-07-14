"""
Standard shape that every extractor produces, ready for embedding + upsert.

Each extractor (extract_readme.py, extract_docstrings.py, extract_git_log.py)
is responsible for finding semantically COMPLETE units (a doc section, a
function+docstring, a commit) — never fixed-character-count splitting,
which would cut a table or a function body in half.
"""
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    source_file: str
    chunk_type: str        # "doc" | "docstring" | "commit"
    project: str
    extra: dict = field(default_factory=dict)   # e.g. {"symbol_name": ...} or {"commit_hash": ..., "date": ...}
