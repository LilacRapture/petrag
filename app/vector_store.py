"""
Qdrant client for QUERY-time reads only.
Kept separate from ingestion/vector_store.py (write-only, ingest-time).
"""
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from .config import settings


@lru_cache
def get_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def search(query_vector: list[float], top_k: int = 5, project: str | None = None):
    """
    Returns a list of qdrant_client.models.ScoredPoint —
    each has .payload (text, source_file, chunk_type, project, ...) and .score.
    """
    client = get_client()

    query_filter = None
    if project:
        query_filter = Filter(
            must=[FieldCondition(key="project", match=MatchValue(value=project))]
        )

    result = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
    )
    return result.points
    