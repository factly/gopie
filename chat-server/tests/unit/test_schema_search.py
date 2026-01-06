import pytest

from app.services.qdrant.schema_search import search_schemas

pytestmark = pytest.mark.unit

import pytest


@pytest.mark.asyncio
async def test_search_schemas_no_filters(monkeypatch):
    captured = {}

    class DummyVS:
        pass

    class DummyDoc:
        def __init__(self, metadata):
            self.metadata = metadata

    def fake_get_vector_store(embeddings):
        captured["vs"] = True
        return DummyVS()

    async def fake_perform_similarity_search(vector_store, query, top_k, query_filter):
        captured["args"] = {
            "query": query,
            "top_k": top_k,
            "filter": query_filter,
        }
        return [
            DummyDoc(
                {
                    "name": "Sales",
                    "dataset_id": "d1",
                    "dataset_name": "sales",
                    "project_id": "p1",
                    "org_id": "org1",
                    "dataset_description": "sales table",
                    "columns": [],
                }
            )
        ]

    monkeypatch.setattr(
        "app.services.qdrant.schema_search.QdrantSetup.get_vector_store",
        fake_get_vector_store,
    )
    monkeypatch.setattr(
        "app.services.qdrant.schema_search.perform_similarity_search",
        fake_perform_similarity_search,
    )

    results = await search_schemas("revenue", embeddings=None, project_ids=None, dataset_ids=None)

    assert len(results) == 1
    assert results[0].dataset_id == "d1"
    assert captured["args"]["filter"] is None


@pytest.mark.asyncio
async def test_search_schemas_with_project_filter(monkeypatch):
    seen = {}

    class DummyVS:
        pass

    def fake_get_vector_store(embeddings):
        return DummyVS()

    async def fake_perform_similarity_search(vector_store, query, top_k, query_filter):
        seen["filter"] = query_filter
        return []

    monkeypatch.setattr(
        "app.services.qdrant.schema_search.QdrantSetup.get_vector_store",
        fake_get_vector_store,
    )
    monkeypatch.setattr(
        "app.services.qdrant.schema_search.perform_similarity_search",
        fake_perform_similarity_search,
    )

    _ = await search_schemas("x", embeddings=None, project_ids=["p1", "p2"], dataset_ids=None)

    assert seen["filter"] is not None
    assert getattr(seen["filter"], "should", None) is not None
    assert len(seen["filter"].should) == 1


@pytest.mark.asyncio
async def test_search_schemas_with_dataset_filter(monkeypatch):
    seen = {}

    class DummyVS:
        pass

    def fake_get_vector_store(embeddings):
        return DummyVS()

    async def fake_perform_similarity_search(vector_store, query, top_k, query_filter):
        seen["filter"] = query_filter
        return []

    monkeypatch.setattr(
        "app.services.qdrant.schema_search.QdrantSetup.get_vector_store",
        fake_get_vector_store,
    )
    monkeypatch.setattr(
        "app.services.qdrant.schema_search.perform_similarity_search",
        fake_perform_similarity_search,
    )

    _ = await search_schemas("x", embeddings=None, project_ids=None, dataset_ids=["d1"])

    assert seen["filter"] is not None
    assert getattr(seen["filter"], "should", None) is not None
    assert len(seen["filter"].should) == 1


@pytest.mark.asyncio
async def test_search_schemas_with_both_filters(monkeypatch):
    seen = {}

    class DummyVS:
        pass

    def fake_get_vector_store(embeddings):
        return DummyVS()

    async def fake_perform_similarity_search(vector_store, query, top_k, query_filter):
        seen["filter"] = query_filter
        return []

    monkeypatch.setattr(
        "app.services.qdrant.schema_search.QdrantSetup.get_vector_store",
        fake_get_vector_store,
    )
    monkeypatch.setattr(
        "app.services.qdrant.schema_search.perform_similarity_search",
        fake_perform_similarity_search,
    )

    _ = await search_schemas("x", embeddings=None, project_ids=["p"], dataset_ids=["d"])

    assert seen["filter"] is not None
    assert getattr(seen["filter"], "should", None) is not None
    assert len(seen["filter"].should) == 2


@pytest.mark.asyncio
async def test_search_schemas_error_returns_empty(monkeypatch):
    """Test that exceptions during search are caught and empty list is returned."""

    def fake_get_vector_store(embeddings):
        return object()

    async def fake_perform_similarity_search(*args, **kwargs):
        raise RuntimeError("qdrant down")

    monkeypatch.setattr(
        "app.services.qdrant.schema_search.QdrantSetup.get_vector_store",
        fake_get_vector_store,
    )
    monkeypatch.setattr(
        "app.services.qdrant.schema_search.perform_similarity_search",
        fake_perform_similarity_search,
    )
    dummy_logger = type(
        "L",
        (),
        {
            "exception": lambda *args, **kwargs: None,
            "debug": lambda *args, **kwargs: None,
        },
    )()
    monkeypatch.setattr("app.services.qdrant.schema_search.logger", dummy_logger)

    results = await search_schemas("x", embeddings=None)
    assert results == []
