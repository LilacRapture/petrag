"""
Tests for app/main.py — covers the happy path and the error-handling
paths added for Qdrant/Ollama unavailability.

Mocks are applied to `app.main.<name>`, not to the origin modules
(`app.vector_store.search`, `app.llm.generate_answer`, etc.) — main.py
imports them by name ("from .vector_store import search"), so the
*reference actually called* by the view function lives on `app.main`,
not on the module it came from. Patching the origin module would have
no effect here.
"""
import httpx
import pytest
from fastapi.testclient import TestClient
from qdrant_client.http.exceptions import ApiException

from app import main as main_module
from app.main import app

client = TestClient(app)


def _dummy_hit(text="some context", source_file="README.md", score=0.9):
    """
    Minimal stand-in for qdrant_client's ScoredPoint — only implements
    the two attributes app/main.py actually reads (.payload, .score).
    """
    return type(
        "FakeHit",
        (),
        {"payload": {"text": text, "source_file": source_file, "chunk_type": "doc"}, "score": score},
    )()


@pytest.fixture(autouse=True)
def _mock_embed(monkeypatch):
    """
    Every /query call hits embed_text() first. Stubbed out everywhere
    so tests don't load the real sentence-transformers model — slow,
    and irrelevant to what these tests check.
    """
    monkeypatch.setattr(main_module, "embed_text", lambda text: [0.0] * 384)


# ---------------------------------------------------------------------------
# App startup (lifespan)
# ---------------------------------------------------------------------------

def test_lifespan_warms_up_embedder_on_startup(monkeypatch):
    warmup_calls = []
    monkeypatch.setattr(main_module, "get_embedder", lambda: warmup_calls.append(True))

    with TestClient(app) as _:
        pass  # entering/exiting the context triggers lifespan startup/shutdown

    assert warmup_calls == [True]


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_query_no_hits_returns_default_message(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *a, **k: [])

    response = client.post("/query", json={"question": "anything?"})

    assert response.status_code == 200
    data = response.json()
    assert data["sources"] == []
    assert "No relevant information" in data["answer"]


def test_query_success_returns_answer_and_sources(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *a, **k: [_dummy_hit()])
    monkeypatch.setattr(main_module, "generate_answer", lambda *a, **k: "The answer is 42.")

    response = client.post("/query", json={"question": "what is it?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The answer is 42."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_file"] == "README.md"


# ---------------------------------------------------------------------------
# Qdrant unavailable
# ---------------------------------------------------------------------------

def test_query_returns_503_on_qdrant_connection_refused(monkeypatch):
    def _raise(*a, **k):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(main_module, "search", _raise)
    response = client.post("/query", json={"question": "anything?"})

    assert response.status_code == 503


def test_query_returns_503_on_qdrant_api_exception(monkeypatch):
    def _raise(*a, **k):
        raise ApiException("collection not found")

    monkeypatch.setattr(main_module, "search", _raise)
    response = client.post("/query", json={"question": "anything?"})

    assert response.status_code == 503


def test_query_returns_503_on_qdrant_timeout(monkeypatch):
    def _raise(*a, **k):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(main_module, "search", _raise)
    response = client.post("/query", json={"question": "anything?"})

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Ollama unavailable
# ---------------------------------------------------------------------------

def test_query_returns_503_on_ollama_connection_refused(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *a, **k: [_dummy_hit()])

    def _raise(*a, **k):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(main_module, "generate_answer", _raise)
    response = client.post("/query", json={"question": "anything?"})

    assert response.status_code == 503


def test_query_returns_504_on_ollama_timeout(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *a, **k: [_dummy_hit()])

    def _raise(*a, **k):
        raise httpx.TimeoutException("model is thinking too long")

    monkeypatch.setattr(main_module, "generate_answer", _raise)
    response = client.post("/query", json={"question": "anything?"})

    assert response.status_code == 504


def test_query_returns_502_on_ollama_error_status(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *a, **k: [_dummy_hit()])

    request = httpx.Request("POST", "http://host.docker.internal:11434/api/generate")
    error_response = httpx.Response(500, request=request)

    def _raise(*a, **k):
        raise httpx.HTTPStatusError("Internal Server Error", request=request, response=error_response)

    monkeypatch.setattr(main_module, "generate_answer", _raise)
    response = client.post("/query", json={"question": "anything?"})

    assert response.status_code == 502
