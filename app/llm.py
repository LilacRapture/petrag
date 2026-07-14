"""
Thin client for the LOCAL Ollama instance running natively on the host
(NOT inside Docker — see docker-compose.yml comments for why: no GPU/Metal
passthrough into containers on Mac).
"""
from .config import settings


def generate_answer(question: str, context_chunks: list[str]) -> str:
    """
    TODO (next iteration step):
    - build a prompt: question + numbered context chunks + explicit
      instruction to say "not found in context" if the answer isn't there
    - POST to f"{settings.ollama_base_url}/api/generate"
      with {"model": settings.ollama_model, "prompt": ..., "stream": False}
    - return response.json()["response"]
    """
    raise NotImplementedError
