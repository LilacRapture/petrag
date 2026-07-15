"""
Wraps sentence-transformers so the rest of the app doesn't care which
embedding model is loaded.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from .config import settings


@lru_cache
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)


def embed_text(text: str) -> list[float]:
    """Single-string embedding — used for the incoming question in app/main.py."""
    embedder = get_embedder()
    return embedder.encode(text, show_progress_bar=False).tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batch embedding — used by ingestion for many chunks at once.
    One call lets sentence-transformers batch internally (much faster
    than one embed_text() call per chunk), and show_progress_bar=False
    stops a bar being printed at all.
    """
    embedder = get_embedder()
    return embedder.encode(texts, show_progress_bar=False).tolist()
