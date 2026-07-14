"""
TODO (Phase 3):
- walk *.py files under source_project_path with pathlib, skipping migrations/
- parse each file with the `ast` module
- for every ClassDef/FunctionDef with a docstring, yield a Chunk
  (text = signature + docstring, chunk_type="docstring",
   extra={"symbol_name": "ClassName.method_name"})
"""
from collections.abc import Iterator

from .chunking import Chunk


def extract(project: str, source_path: str) -> Iterator[Chunk]:
    raise NotImplementedError
