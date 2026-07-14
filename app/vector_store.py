"""
Qdrant client for QUERY-time reads only.
Collection creation / upsert logic lives in ingestion/vector_store.py.
"""
from qdrant_client import QdrantClient

from .config import settings


def get_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def search(query_vector: list[float], top_k: int = 5, project: str | None = None):
    """
    TODO (next iteration step):
    - if project is given, build a qdrant_client.models.Filter on
      payload["project"] == project
    - client.search(collection_name=settings.qdrant_collection,
                     query_vector=query_vector, limit=top_k, query_filter=...)
    - return the list of hits (each has .payload and .score)
    """
    raise NotImplementedError
