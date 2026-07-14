"""
Thin client for the LOCAL Ollama instance running natively on the host
(NOT inside Docker — see docker-compose.yml for why: no GPU/Metal
passthrough into containers on Mac).
"""
import httpx

from .config import settings

_PROMPT_TEMPLATE = """You help answer questions about a pet project called {project}.

Context (relevant excerpts from the project's code/documentation):
{context}

Question: {question}

Answer ONLY using the context above. If the answer isn't in the context, \
say so explicitly instead of guessing.
"""


def _build_prompt(question: str, context_chunks: list[str], project: str) -> str:
    numbered_context = "\n\n".join(
        f"[{i + 1}] {chunk}" for i, chunk in enumerate(context_chunks)
    )
    return _PROMPT_TEMPLATE.format(project=project, context=numbered_context, question=question)


def generate_answer(question: str, context_chunks: list[str], project: str) -> str:
    prompt = _build_prompt(question, context_chunks, project)

    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120.0,  # generous margin, Ollama loads the model into memory on first call
    )
    response.raise_for_status()
    return response.json()["response"]
