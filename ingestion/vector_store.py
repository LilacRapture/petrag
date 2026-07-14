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
    """Create the collection if it doesn't exist yet. Idempotent — same
    spirit as seed_roles.py's get_or_create in TaskTracker."""
    if not client.collection_exists(settings.qdrant_collection):
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def upsert_chunks(client: QdrantClient, chunks: list, vectors: list[list[float]]) -> None:
    """
    Each chunk gets a fresh random UUID as its point id. That means
    re-running ingestion on unchanged files creates DUPLICATE points
    rather than updating existing ones — acceptable for Phase 1 (single
    manual run), but worth flagging now: real re-ingestion support will
    need a deterministic id (e.g. hash of source_file + heading) so
    upsert overwrites instead of duplicating. Revisit when we design
    incremental re-indexing.
    """
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
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
