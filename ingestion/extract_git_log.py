"""
TODO (Phase 4):
- subprocess.run(["git", "log", "--stat"], cwd=source_path, capture_output=True)
- parse into one Chunk per commit (message + changed files)
- yield Chunk(..., chunk_type="commit", extra={"commit_hash": ..., "date": ...})
"""
from collections.abc import Iterator

from .chunking import Chunk


def extract(project: str, source_path: str) -> Iterator[Chunk]:
    raise NotImplementedError
