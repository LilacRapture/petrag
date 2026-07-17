"""
Tests for app/llm.py — prompt construction and the Ollama HTTP call.

httpx.post is patched at the module level (llm.httpx.post), not via a
mocked client instance, because llm.py calls it as a bare module
function ("httpx.post(...)"), not through a client object.
"""
import httpx
import pytest

from app import llm


def test_build_prompt_includes_question_and_project():
    prompt = llm._build_prompt("What is X?", ["chunk one"], "myproject")

    assert "myproject" in prompt
    assert "What is X?" in prompt
    assert "chunk one" in prompt


def test_build_prompt_numbers_context_chunks_starting_at_one():
    prompt = llm._build_prompt("q", ["first chunk", "second chunk"], "proj")

    assert "[1] first chunk" in prompt
    assert "[2] second chunk" in prompt


def test_generate_answer_posts_expected_payload_to_ollama(monkeypatch):
    captured = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "42"}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(llm.httpx, "post", fake_post)

    answer = llm.generate_answer("What is it?", ["ctx one", "ctx two"], "myproject")

    assert answer == "42"
    assert captured["url"] == f"{llm.settings.ollama_base_url}/api/generate"
    assert captured["json"]["model"] == llm.settings.ollama_model
    assert captured["json"]["stream"] is False
    assert "What is it?" in captured["json"]["prompt"]
    assert captured["timeout"] == 120.0


def test_generate_answer_propagates_http_status_error(monkeypatch):
    """
    generate_answer() must not swallow errors — app/main.py's error
    handling (HTTPStatusError -> 502) relies on this propagating.
    """

    class _FailingResponse:
        def raise_for_status(self):
            request = httpx.Request("POST", "http://fake")
            response = httpx.Response(500, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

        def json(self):
            raise AssertionError("json() must not be called if raise_for_status() raised")

    monkeypatch.setattr(llm.httpx, "post", lambda url, json, timeout: _FailingResponse())

    with pytest.raises(httpx.HTTPStatusError):
        llm.generate_answer("question", ["ctx"], "myproject")
        