"""
Tests for app/vector_store.py::search() — the read-time Qdrant client.

Only get_client() is mocked out — search() itself, including the
Filter/FieldCondition construction for the `project` payload filter
(the mechanism ADR-011 in docs/decisions.md relies on for multi-project
isolation), runs for real.
"""
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app import vector_store


class _FakeQueryResult:
    def __init__(self, points):
        self.points = points


class _FakeClient:
    """Records every call to query_points() so tests can inspect the
    exact arguments search() built, instead of guessing from behavior."""

    def __init__(self):
        self.calls = []

    def query_points(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeQueryResult(points=["fake-point-1", "fake-point-2"])


def test_search_without_project_uses_no_filter(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(vector_store, "get_client", lambda: fake_client)

    result = vector_store.search([0.1, 0.2, 0.3], top_k=5, project=None)

    assert result == ["fake-point-1", "fake-point-2"]
    assert fake_client.calls[0]["query_filter"] is None


def test_search_with_project_builds_matching_filter(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(vector_store, "get_client", lambda: fake_client)

    vector_store.search([0.1, 0.2, 0.3], top_k=5, project="tasktracker")

    query_filter = fake_client.calls[0]["query_filter"]
    assert isinstance(query_filter, Filter)
    assert len(query_filter.must) == 1

    condition = query_filter.must[0]
    assert isinstance(condition, FieldCondition)
    assert condition.key == "project"
    assert isinstance(condition.match, MatchValue)
    assert condition.match.value == "tasktracker"


def test_search_passes_through_collection_name_top_k_and_vector(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(vector_store, "get_client", lambda: fake_client)

    vector_store.search([0.1], top_k=3, project=None)

    call = fake_client.calls[0]
    assert call["collection_name"] == vector_store.settings.qdrant_collection
    assert call["limit"] == 3
    assert call["query"] == [0.1]
    