"""
Wraps sentence-transformers so the rest of the app doesn't care which
embedding model is loaded.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from .config import settings


@lru_cache
def get_embedder() -> SentenceTransformer:
    # Cached: loading the model is expensive, we want one instance per process.
    return SentenceTransformer(settings.embedding_model)


def embed_text(text: str) -> list[float]:
    embedder = get_embedder()
    return embedder.encode(text).tolist()
