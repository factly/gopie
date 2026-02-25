from unittest.mock import AsyncMock, Mock, patch

import pytest
from qdrant_client import models

from app.services.qdrant.schema_search import search_schemas

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_search_schemas_no_filters():
    """Test search_schemas without filters returns results correctly."""
    mock_embeddings = Mock()
    mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]

    mock_client = AsyncMock()
    mock_point = Mock()
    mock_point.payload = {
        "metadata": {
            "name": "Sales",
            "dataset_id": "d1",
            "dataset_name": "sales",
            "project_id": "p1",
            "org_id": "org1",
            "dataset_description": "sales table",
            "columns": [],
        }
    }
    mock_client.query_points.return_value = Mock(points=[mock_point])

    with (
        patch(
            "app.services.qdrant.schema_search.QdrantSetup.get_async_client",
            return_value=mock_client,
        ),
        patch("app.services.qdrant.schema_search.generate_sparse_vector") as mock_sparse,
    ):
        mock_sparse.return_value = models.SparseVector(indices=[1, 2], values=[0.5, 0.5])

        results = await search_schemas(
            "revenue", embeddings=mock_embeddings, project_ids=None, dataset_ids=None
        )

        assert len(results) == 1
        assert results[0].dataset_id == "d1"

        # Verify query_points was called with correct structure
        call_args = mock_client.query_points.call_args
        assert call_args.kwargs["prefetch"][0].filter is None
        assert len(call_args.kwargs["prefetch"]) == 2  # Dense and sparse prefetch


@pytest.mark.asyncio
async def test_search_schemas_with_project_filter():
    """Test search_schemas with project_ids filter."""
    mock_embeddings = Mock()
    mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]

    mock_client = AsyncMock()
    mock_client.query_points.return_value = Mock(points=[])

    with (
        patch(
            "app.services.qdrant.schema_search.QdrantSetup.get_async_client",
            return_value=mock_client,
        ),
        patch("app.services.qdrant.schema_search.generate_sparse_vector") as mock_sparse,
    ):
        mock_sparse.return_value = models.SparseVector(indices=[1, 2], values=[0.5, 0.5])

        _ = await search_schemas(
            "x", embeddings=mock_embeddings, project_ids=["p1", "p2"], dataset_ids=None
        )

        call_args = mock_client.query_points.call_args
        query_filter = call_args.kwargs.get("filter") or call_args.kwargs["prefetch"][0].filter

        assert query_filter is not None
        assert hasattr(query_filter, "should")
        assert len(query_filter.should) == 1  # Only project_ids filter
        assert not hasattr(query_filter, "must") or not query_filter.must


@pytest.mark.asyncio
async def test_search_schemas_with_dataset_filter():
    """Test search_schemas with dataset_ids filter."""
    mock_embeddings = Mock()
    mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]

    mock_client = AsyncMock()
    mock_client.query_points.return_value = Mock(points=[])

    with (
        patch(
            "app.services.qdrant.schema_search.QdrantSetup.get_async_client",
            return_value=mock_client,
        ),
        patch("app.services.qdrant.schema_search.generate_sparse_vector") as mock_sparse,
    ):
        mock_sparse.return_value = models.SparseVector(indices=[1, 2], values=[0.5, 0.5])

        _ = await search_schemas(
            "x", embeddings=mock_embeddings, project_ids=None, dataset_ids=["d1"]
        )

        call_args = mock_client.query_points.call_args
        query_filter = call_args.kwargs.get("filter") or call_args.kwargs["prefetch"][0].filter

        assert query_filter is not None
        assert hasattr(query_filter, "should")
        assert len(query_filter.should) == 1  # Only dataset_ids filter


@pytest.mark.asyncio
async def test_search_schemas_with_both_filters():
    """Test search_schemas with both project_ids and dataset_ids filters."""
    mock_embeddings = Mock()
    mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]

    mock_client = AsyncMock()
    mock_client.query_points.return_value = Mock(points=[])

    with (
        patch(
            "app.services.qdrant.schema_search.QdrantSetup.get_async_client",
            return_value=mock_client,
        ),
        patch("app.services.qdrant.schema_search.generate_sparse_vector") as mock_sparse,
    ):
        mock_sparse.return_value = models.SparseVector(indices=[1, 2], values=[0.5, 0.5])

        _ = await search_schemas(
            "x", embeddings=mock_embeddings, project_ids=["p"], dataset_ids=["d"]
        )

        call_args = mock_client.query_points.call_args
        query_filter = call_args.kwargs.get("filter") or call_args.kwargs["prefetch"][0].filter

        assert query_filter is not None
        assert hasattr(query_filter, "should")
        assert len(query_filter.should) == 2  # Both project_ids and dataset_ids filters


@pytest.mark.asyncio
async def test_search_schemas_with_org_filter():
    """Test search_schemas with org_id filter."""
    mock_embeddings = Mock()
    mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]

    mock_client = AsyncMock()
    mock_client.query_points.return_value = Mock(points=[])

    with (
        patch(
            "app.services.qdrant.schema_search.QdrantSetup.get_async_client",
            return_value=mock_client,
        ),
        patch("app.services.qdrant.schema_search.generate_sparse_vector") as mock_sparse,
    ):
        mock_sparse.return_value = models.SparseVector(indices=[1, 2], values=[0.5, 0.5])

        _ = await search_schemas("x", embeddings=mock_embeddings, org_id="org123")

        call_args = mock_client.query_points.call_args
        query_filter = call_args.kwargs.get("filter") or call_args.kwargs["prefetch"][0].filter

        assert query_filter is not None
        assert hasattr(query_filter, "must")
        assert len(query_filter.must) == 1  # Only org_id filter


@pytest.mark.asyncio
async def test_search_schemas_error_returns_empty():
    """Test that exceptions during search are caught and empty list is returned."""
    mock_embeddings = Mock()
    mock_embeddings.embed_query.side_effect = RuntimeError("qdrant down")

    with patch("app.services.qdrant.schema_search.logger") as mock_logger:
        results = await search_schemas("x", embeddings=mock_embeddings)
        assert results == []
        mock_logger.exception.assert_called_once()
