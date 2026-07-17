"""
CLI entrypoint for the ingestion pipeline.

Usage (run from the petrag/ root, with the venv active):
    python -m ingestion.ingest --source readme

Qdrant must be running first: docker-compose up -d qdrant

If running from the host venv (not from inside the api container), the
default QDRANT_HOST="qdrant" in .env won't resolve — that hostname only
exists inside the docker-compose network. Override it for local runs:
    QDRANT_HOST=localhost python -m ingestion.ingest --source readme
"""
import argparse
import logging

from app.config import settings
from app.embeddings import embed_texts
from ingestion import extract_docstrings, extract_git_log, extract_readme
from ingestion.vector_store import ensure_collection, get_client, upsert_chunks

logger = logging.getLogger(__name__)

EXTRACTORS = {
    "readme": extract_readme.extract,
    "docstrings": extract_docstrings.extract,
    "git_log": extract_git_log.extract,
}


def run(source: str, project: str, source_path: str) -> None:
    extractor = EXTRACTORS[source]

    chunks = list(extractor(project, source_path))
    if not chunks:
        logger.info("No chunks extracted from source=%r at %r", source, source_path)
        return
    logger.info("Extracted %d chunks from source=%r", len(chunks), source)

    logger.info("Embedding chunks...")
    vectors = embed_texts([chunk.text for chunk in chunks])

    client = get_client()
    ensure_collection(client, vector_size=len(vectors[0]))
    upsert_chunks(client, chunks, vectors)

    by_type: dict[str, int] = {}
    for chunk in chunks:
        by_type[chunk.chunk_type] = by_type.get(chunk.chunk_type, 0) + 1
    logger.info("Indexed into Qdrant collection '%s': %s", settings.qdrant_collection, by_type)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="PetRAG ingestion pipeline")
    parser.add_argument(
        "--source",
        choices=sorted(EXTRACTORS),
        required=True,
        help="Which extractor to run",
    )
    parser.add_argument(
        "--project",
        default=settings.source_project_name,
        help=f"Project name stored in chunk metadata (default from .env: {settings.source_project_name!r})",
    )
    parser.add_argument(
        "--path",
        default=settings.source_project_path,
        help=f"Path to the project checkout (default from .env: {settings.source_project_path!r})",
    )
    args = parser.parse_args()

    run(args.source, args.project, args.path)


if __name__ == "__main__":
    main()
    