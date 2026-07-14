"""
Qdrant client for INGEST-time writes (create_collection, upsert).
Kept separate from app/vector_store.py (read-only, query-time).

client is passed into ensure_collection/upsert_chunks explicitly rather
than created internally on every call — cheap dependency injection that
keeps these functions easy to test and avoids opening a new connection
per call.
"""
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings


def get_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection(client: QdrantClient, vector_size: int) -> None:
    if not client.collection_exists(settings.qdrant_collection):
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def _chunk_id(chunk) -> str:
    """
    Deterministic point id: re-running ingestion on the SAME section
    (identified by project + chunk_type + source_file + its distinguishing
    extra fields — e.g. heading for docs, symbol_name for docstrings,
    commit_hash for commits) overwrites the existing point instead of
    creating a duplicate, since Qdrant's upsert is id-keyed.

    Deliberately excludes chunk.text from the key — editing a section's
    content should still update the same point, not spawn a new one.
    """
    extra_key = ",".join(f"{k}={v}" for k, v in sorted(chunk.extra.items()))
    natural_key = f"{chunk.project}:{chunk.chunk_type}:{chunk.source_file}:{extra_key}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, natural_key))


def upsert_chunks(client: QdrantClient, chunks: list, vectors: list[list[float]]) -> None:
    points = [
        PointStruct(
            id=_chunk_id(chunk),
            vector=vector,
            payload={
                "text": chunk.text,
                "source_file": chunk.source_file,
                "chunk_type": chunk.chunk_type,
                "project": chunk.project,
                **chunk.extra,
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)
