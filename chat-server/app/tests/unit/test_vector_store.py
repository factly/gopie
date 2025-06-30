"""Tests for vector store functionality."""

from unittest.mock import Mock, patch

import pytest

from app.services.qdrant.schema_search import search_schemas
from app.services.qdrant.vector_store import (
    add_documents_to_vector_store,
    perform_similarity_search,
)


class TestVectorStore:
    """Test cases for vector store operations."""

    @pytest.fixture
    def mock_documents(self):
        """Mock documents for testing."""
        return [
            Mock(
                page_content="Test document 1",
                metadata={
                    "project_id": "proj1",
                    "dataset_id": "ds1",
                    "dataset_name": "test_dataset_1",
                },
            ),
            Mock(
                page_content="Test document 2",
                metadata={
                    "project_id": "proj2",
                    "dataset_id": "ds2",
                    "dataset_name": "test_dataset_2",
                },
            ),
        ]

    @pytest.mark.asyncio
    async def test_add_documents_to_vector_store_success(
        self, mock_documents, mock_vector_store, mock_qdrant_client
    ):
        """Test successful addition of documents to vector store."""
        with (
            patch(
                "app.services.qdrant.vector_store.ModelProvider"
            ) as mock_provider,
            patch(
                "app.services.qdrant.vector_store.setup_vector_store"
            ) as mock_setup,
            patch(
                "app.services.qdrant.vector_store.initialize_qdrant_client"
            ) as mock_init_client,
        ):

            # Setup mocks
            mock_provider.return_value.get_embeddings_model.return_value = (
                Mock()
            )
            mock_setup.return_value = mock_vector_store
            mock_init_client.return_value = mock_qdrant_client
            mock_qdrant_client.scroll.return_value = (
                [],
                None,
            )  # No existing documents

            # Execute
            await add_documents_to_vector_store(mock_documents)

            # Assertions
            mock_vector_store.add_documents.assert_called_once()
            call_args = mock_vector_store.add_documents.call_args
            assert len(call_args.kwargs["documents"]) == 2
            assert len(call_args.kwargs["ids"]) == 2

    @pytest.mark.asyncio
    async def test_add_documents_skip_existing(
        self, mock_documents, mock_vector_store, mock_qdrant_client
    ):
        """Test that existing documents are skipped."""
        with (
            patch(
                "app.services.qdrant.vector_store.ModelProvider"
            ) as mock_provider,
            patch(
                "app.services.qdrant.vector_store.setup_vector_store"
            ) as mock_setup,
            patch(
                "app.services.qdrant.vector_store.initialize_qdrant_client"
            ) as mock_init_client,
        ):

            # Setup mocks
            mock_provider.return_value.get_embeddings_model.return_value = (
                Mock()
            )
            mock_setup.return_value = mock_vector_store
            mock_init_client.return_value = mock_qdrant_client
            # First document exists, second doesn't
            mock_qdrant_client.scroll.side_effect = [
                ([Mock()], None),  # Document exists
                ([], None),  # Document doesn't exist
            ]

            # Execute
            await add_documents_to_vector_store(mock_documents)

            # Assertions - only one document should be added
            mock_vector_store.add_documents.assert_called_once()
            call_args = mock_vector_store.add_documents.call_args
            assert len(call_args.kwargs["documents"]) == 1
            assert call_args.kwargs["documents"][0] == mock_documents[1]

    @pytest.mark.asyncio
    async def test_add_documents_with_custom_ids(
        self, mock_documents, mock_vector_store, mock_qdrant_client
    ):
        """Test adding documents with custom IDs."""
        custom_ids = ["custom_id_1", "custom_id_2"]

        with (
            patch(
                "app.services.qdrant.vector_store.ModelProvider"
            ) as mock_provider,
            patch(
                "app.services.qdrant.vector_store.setup_vector_store"
            ) as mock_setup,
            patch(
                "app.services.qdrant.vector_store.initialize_qdrant_client"
            ) as mock_init_client,
        ):

            mock_provider.return_value.get_embeddings_model.return_value = (
                Mock()
            )
            mock_setup.return_value = mock_vector_store
            mock_init_client.return_value = mock_qdrant_client
            mock_qdrant_client.scroll.return_value = ([], None)

            # Execute
            await add_documents_to_vector_store(mock_documents, ids=custom_ids)

            # Assertions
            mock_vector_store.add_documents.assert_called_once()
            call_args = mock_vector_store.add_documents.call_args
            assert call_args.kwargs["ids"] == custom_ids

    def test_perform_similarity_search_success(self, mock_vector_store):
        """Test successful similarity search."""
        mock_results = [
            Mock(page_content="Result 1", metadata={"score": 0.9}),
            Mock(page_content="Result 2", metadata={"score": 0.8}),
        ]
        mock_vector_store.similarity_search.return_value = mock_results

        # Execute
        results = perform_similarity_search(
            vector_store=mock_vector_store, query="test query", top_k=5
        )

        # Assertions
        assert results == mock_results
        mock_vector_store.similarity_search.assert_called_once_with(
            "test query", k=5, filter=None
        )

    def test_perform_similarity_search_with_filter(self, mock_vector_store):
        """Test similarity search with filter."""
        query_filter = Mock()
        mock_results = [Mock()]
        mock_vector_store.similarity_search.return_value = mock_results

        # Execute
        results = perform_similarity_search(
            vector_store=mock_vector_store,
            query="test query",
            top_k=3,
            query_filter=query_filter,
        )

        # Assertions
        assert results == mock_results
        mock_vector_store.similarity_search.assert_called_once_with(
            "test query", k=3, filter=query_filter
        )

    def test_perform_similarity_search_fallback_on_error(
        self, mock_vector_store
    ):
        """Test fallback to unfiltered search when filtered search fails."""
        query_filter = Mock()
        mock_vector_store.similarity_search.side_effect = [
            Exception("Filter error"),  # First call with filter fails
            [Mock()],  # Second call without filter succeeds
        ]

        # Execute
        results = perform_similarity_search(
            vector_store=mock_vector_store,
            query="test query",
            query_filter=query_filter,
        )

        # Assertions
        assert len(results) == 1
        assert mock_vector_store.similarity_search.call_count == 2

    def test_perform_similarity_search_raises_on_unfiltered_error(
        self, mock_vector_store
    ):
        """Test that errors are raised when unfiltered search also fails."""
        mock_vector_store.similarity_search.side_effect = Exception(
            "Vector store error"
        )

        # Execute & Assert
        with pytest.raises(Exception, match="Vector store error"):
            perform_similarity_search(
                vector_store=mock_vector_store, query="test query"
            )


class TestSchemaSearch:
    """Test cases for schema search functionality."""

    @pytest.mark.asyncio
    async def test_search_schemas_success(self, mock_embeddings):
        """Test successful schema search."""
        mock_results = [
            Mock(page_content='{"dataset_name": "test1", "columns": []}'),
            Mock(page_content='{"dataset_name": "test2", "columns": []}'),
        ]

        with (
            patch(
                "app.services.qdrant.schema_search.setup_vector_store"
            ) as mock_setup,
            patch(
                "app.services.qdrant.schema_search.perform_similarity_search"
            ) as mock_search,
        ):

            mock_vector_store = Mock()
            mock_setup.return_value = mock_vector_store
            mock_search.return_value = mock_results

            # Execute
            schemas = await search_schemas(
                user_query="find datasets", embeddings=mock_embeddings, top_k=5
            )

            # Assertions
            assert len(schemas) == 2
            assert schemas[0]["dataset_name"] == "test1"
            assert schemas[1]["dataset_name"] == "test2"

    @pytest.mark.asyncio
    async def test_search_schemas_with_filters(self, mock_embeddings):
        """Test schema search with project and dataset filters."""
        mock_results = [Mock(page_content='{"dataset_name": "filtered_test"}')]

        with (
            patch(
                "app.services.qdrant.schema_search.setup_vector_store"
            ) as mock_setup,
            patch(
                "app.services.qdrant.schema_search.perform_similarity_search"
            ) as mock_search,
        ):

            mock_setup.return_value = Mock()
            mock_search.return_value = mock_results

            # Execute
            schemas = await search_schemas(
                user_query="find datasets",
                embeddings=mock_embeddings,
                project_ids=["proj1", "proj2"],
                dataset_ids=["ds1"],
                top_k=3,
            )

            # Assertions
            assert len(schemas) == 1
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args.kwargs["query_filter"] is not None
            assert call_args.kwargs["top_k"] == 3

    @pytest.mark.asyncio
    async def test_search_schemas_handles_exceptions(self, mock_embeddings):
        """Test that schema search handles exceptions gracefully."""
        with patch(
            "app.services.qdrant.schema_search.setup_vector_store"
        ) as mock_setup:
            mock_setup.side_effect = Exception("Vector store error")

            # Execute
            schemas = await search_schemas(
                user_query="find datasets", embeddings=mock_embeddings
            )

            # Assertions
            assert schemas == []

    @pytest.mark.asyncio
    async def test_search_schemas_empty_results(self, mock_embeddings):
        """Test schema search with no results."""
        with (
            patch(
                "app.services.qdrant.schema_search.setup_vector_store"
            ) as mock_setup,
            patch(
                "app.services.qdrant.schema_search.perform_similarity_search"
            ) as mock_search,
        ):

            mock_setup.return_value = Mock()
            mock_search.return_value = []

            # Execute
            schemas = await search_schemas(
                user_query="nonexistent query", embeddings=mock_embeddings
            )

            # Assertions
            assert schemas == []
