from typing import Union, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.services.qdrant.schema_search import search_schemas
from app.services.qdrant.schema_vectorization import (
    delete_schema_from_qdrant,
    store_schema_in_qdrant,
)
from app.services.qdrant.vector_store import add_document_to_vector_store

pytestmark = pytest.mark.unit


class TestVectorStore:
    @pytest.fixture
    def mock_document(self):
        """
        Provides a sample Document instance with predefined page content and metadata for testing purposes.

        Returns:
            Document: A Document object containing test content and metadata fields for project and dataset identification.
        """
        return Document(
            page_content="test content",
            metadata={
                "project_id": "proj1",
                "dataset_id": "ds1",
                "other_meta": "value",
            },
        )

    @pytest.fixture
    def mock_embeddings(self):
        """
        Provides a mock embeddings object with a stubbed `embed_query` method returning a fixed vector.

        Returns:
            Mock: An object simulating an embeddings interface for testing purposes.
        """
        embeddings = Mock()
        embeddings.embed_query = Mock(return_value=[0.1, 0.2, 0.3])
        return embeddings

    @pytest.mark.asyncio
    async def test_add_document_to_vector_store(self, mock_document):
        """
        Test that a document is correctly added to the vector store with the expected document ID and embeddings.

        Verifies that the vector store and document ID are obtained using the appropriate methods and that the document is added asynchronously with the correct parameters.
        """
        mock_client = AsyncMock()
        mock_client.upsert = AsyncMock()

        with (
            patch("app.services.qdrant.vector_store.QdrantSetup") as mock_qdrant_setup_class,
            patch("app.services.qdrant.vector_store.get_model_provider") as mock_get_model_provider,
        ):
            mock_qdrant_setup_class.get_async_client = AsyncMock(return_value=mock_client)
            mock_qdrant_setup_class.get_document_id.return_value = "doc_id_123"

            mock_model_provider = Mock()
            mock_embeddings = Mock()
            mock_embeddings.embed_query.return_value = [0.1, 0.2]
            mock_model_provider.get_embeddings_model.return_value = mock_embeddings
            mock_get_model_provider.return_value = mock_model_provider

            await add_document_to_vector_store(mock_document)

            mock_qdrant_setup_class.get_async_client.assert_called_once_with("dataset_collection")
            mock_qdrant_setup_class.get_document_id.assert_called_once_with("proj1", "ds1")
            mock_client.upsert.assert_called_once()

            # Verify call args structure
            call_args = mock_client.upsert.call_args
            assert call_args.kwargs["collection_name"] == "dataset_collection"
            assert len(call_args.kwargs["points"]) == 1
            point = call_args.kwargs["points"][0]
            assert point.id == "doc_id_123"
            assert "dense" in point.vector
            assert "sparse" in point.vector


class TestSchemaSearch:
    @pytest.fixture
    def mock_embeddings(self):
        """
        Create a mock OpenAIEmbeddings instance with a stubbed embed_query method returning a fixed vector.

        Returns:
            OpenAIEmbeddings: A mock embeddings object for testing purposes.
        """
        embeddings = Mock(spec=OpenAIEmbeddings)
        embeddings.embed_query = Mock(return_value=[0.1, 0.2, 0.3])
        return cast(OpenAIEmbeddings, embeddings)

    @pytest.mark.asyncio
    async def test_search_schemas_success(self, mock_embeddings):
        """
        Test that `search_schemas` returns a list of schema objects when hybrid search finds matching results.

        Verifies that the function correctly processes multiple results with required metadata fields and returns schema objects with expected names.
        """
        with (
            patch(
                "app.services.qdrant.schema_search.QdrantSetup.get_async_client"
            ) as mock_get_client,
            patch("app.services.qdrant.schema_search.generate_sparse_vector") as mock_sparse,
        ):
            mock_client = AsyncMock()
            mock_point1 = Mock()
            mock_point1.payload = {
                "metadata": {
                    "name": "test1",
                    "dataset_name": "test1",
                    "dataset_description": "Test dataset 1",
                    "project_id": "proj1",
                    "org_id": "org1",
                    "dataset_id": "ds1",
                    "columns": [],
                }
            }
            mock_point2 = Mock()
            mock_point2.payload = {
                "metadata": {
                    "name": "test2",
                    "dataset_name": "test2",
                    "dataset_description": "Test dataset 2",
                    "project_id": "proj2",
                    "org_id": "org2",
                    "dataset_id": "ds2",
                    "columns": [],
                }
            }
            mock_client.query_points.return_value = Mock(points=[mock_point1, mock_point2])
            mock_get_client.return_value = mock_client
            from qdrant_client import models

            mock_sparse.return_value = models.SparseVector(indices=[1, 2], values=[0.5, 0.5])

            schemas = await search_schemas(user_query="test query", embeddings=mock_embeddings)

            assert len(schemas) == 2
            assert schemas[0].name == "test1"
            assert schemas[1].name == "test2"

    @pytest.mark.asyncio
    async def test_search_schemas_with_filters(self, mock_embeddings):
        """
        Test that `search_schemas` returns schemas filtered by project and dataset IDs.

        Verifies that the function returns only schemas matching the specified filters and that the schema's name matches the expected value.
        """
        with (
            patch(
                "app.services.qdrant.schema_search.QdrantSetup.get_async_client"
            ) as mock_get_client,
            patch("app.services.qdrant.schema_search.generate_sparse_vector") as mock_sparse,
        ):
            mock_client = AsyncMock()
            mock_point = Mock()
            mock_point.payload = {
                "metadata": {
                    "name": "filtered_test",
                    "dataset_name": "filtered_test",
                    "dataset_description": "Filtered test dataset",
                    "project_id": "proj1",
                    "org_id": "org1",
                    "dataset_id": "ds1",
                    "columns": [],
                }
            }
            mock_client.query_points.return_value = Mock(points=[mock_point])
            mock_get_client.return_value = mock_client
            from qdrant_client import models

            mock_sparse.return_value = models.SparseVector(indices=[1, 2], values=[0.5, 0.5])

            schemas = await search_schemas(
                user_query="test query",
                embeddings=mock_embeddings,
                project_ids=["proj1"],
                dataset_ids=["ds1"],
            )

            assert len(schemas) == 1
            assert schemas[0].name == "filtered_test"

    @pytest.mark.asyncio
    async def test_search_schemas_handles_exceptions(self, mock_embeddings):
        """
        Test that search_schemas returns an empty list when an exception occurs during hybrid search.
        """
        with (
            patch(
                "app.services.qdrant.schema_search.QdrantSetup.get_async_client"
            ) as mock_get_client,
            patch("app.services.qdrant.schema_search.logger") as mock_logger,
        ):
            mock_client = AsyncMock()
            mock_client.query_points.side_effect = Exception("Search error")
            mock_get_client.return_value = mock_client

            schemas = await search_schemas(user_query="test query", embeddings=mock_embeddings)
            assert schemas == []
            # Verify that the exception was logged
            mock_logger.exception.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_schemas_empty_results(self, mock_embeddings):
        """
        Test that `search_schemas` returns an empty list when the hybrid search yields no results.
        """
        with (
            patch(
                "app.services.qdrant.schema_search.QdrantSetup.get_async_client"
            ) as mock_get_client,
            patch("app.services.qdrant.schema_search.generate_sparse_vector") as mock_sparse,
        ):
            mock_client = AsyncMock()
            mock_client.query_points.return_value = Mock(points=[])
            mock_get_client.return_value = mock_client
            from qdrant_client import models

            mock_sparse.return_value = models.SparseVector(indices=[1, 2], values=[0.5, 0.5])

            schemas = await search_schemas(user_query="test query", embeddings=mock_embeddings)
            assert schemas == []


class TestSchemaVectorization:
    @pytest.mark.asyncio
    async def test_store_schema_in_qdrant_success(self):
        # Create mock data with proper typing for SQL_RESPONSE_TYPE
        """
        Test that storing a schema in Qdrant succeeds when all dependent operations complete without error.

        This test verifies that the schema creation, column description generation, schema formatting, and document addition functions are called as expected, and that the overall operation returns True.
        """
        dataset_summary = Mock()
        sample_data: list[dict[str, Union[str, int, float, None]]] = [
            {"col1": "value1", "col2": 42, "col3": 3.14, "col4": None}
        ]
        dataset_details = Mock()
        project_details = Mock()
        project_details.id = "proj1"

        with (
            patch(
                "app.services.qdrant.schema_vectorization.create_dataset_schema"
            ) as mock_create_schema,
            patch(
                "app.services.qdrant.schema_vectorization.add_document_to_vector_store"
            ) as mock_add_document,
            patch(
                "app.services.qdrant.schema_vectorization.format_schema_for_embedding"
            ) as mock_format_schema,
        ):
            # Create a mock column with a real string column_name
            mock_column = Mock()
            mock_column.column_name = "col1"

            mock_schema = Mock()
            mock_schema.columns = [mock_column]
            # Mock the model_dump method to return a proper dictionary
            mock_schema.model_dump.return_value = {
                "name": "test_schema",
                "dataset_name": "test_schema",
                "dataset_description": "Test description",
                "project_id": "proj1",
                "dataset_id": "ds1",
            }
            mock_create_schema.return_value = mock_schema
            mock_format_schema.return_value = "formatted schema content"
            mock_add_document.return_value = None

            result = await store_schema_in_qdrant(
                dataset_summary, sample_data, dataset_details, project_details, org_id="org1"
            )

            assert result is True
            mock_create_schema.assert_called_once()
            mock_add_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_schema_in_qdrant_failure(self):
        """
        Test that `store_schema_in_qdrant` returns False when an exception occurs during schema creation.
        """
        dataset_summary = Mock()
        sample_data: list[dict[str, Union[str, int, float, None]]] = [
            {"col1": "value1", "col2": 42}
        ]
        dataset_details = Mock()
        project_details = Mock()
        project_details.id = "proj1"

        with (
            patch(
                "app.services.qdrant.schema_vectorization.create_dataset_schema"
            ) as mock_create_schema,
            patch("app.services.qdrant.schema_vectorization.logger") as mock_logger,
        ):
            mock_create_schema.side_effect = Exception("Storage error")

            result = await store_schema_in_qdrant(
                dataset_summary, sample_data, dataset_details, project_details, org_id="org1"
            )
            assert result is False
            # Verify that the exception was logged
            mock_logger.exception.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_schema_from_qdrant_success(self):
        """
        Test that deleting a schema from Qdrant succeeds and returns True.

        Verifies that the async client's delete method is called and the function returns True when deletion is successful.
        """
        with (
            patch(
                "app.services.qdrant.schema_vectorization.QdrantSetup"
            ) as mock_qdrant_setup_class,
        ):
            mock_async_client = Mock()
            mock_async_client.delete = AsyncMock()  # Only the delete method needs to be async
            mock_qdrant_setup_class.get_async_client = AsyncMock(return_value=mock_async_client)
            mock_qdrant_setup_class.get_document_id.return_value = "schema_id_123"

            result = await delete_schema_from_qdrant("ds1", "proj1")

            assert result is True
            mock_qdrant_setup_class.get_async_client.assert_called_once()
            mock_async_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_schema_from_qdrant_failure(self):
        """
        Test that `delete_schema_from_qdrant` returns False when an exception occurs during schema deletion.
        """
        with (
            patch(
                "app.services.qdrant.schema_vectorization.QdrantSetup"
            ) as mock_qdrant_setup_class,
            patch("app.services.qdrant.schema_vectorization.logger") as mock_logger,
        ):
            mock_async_client = Mock()
            mock_async_client.delete = AsyncMock(side_effect=Exception("Delete error"))
            mock_qdrant_setup_class.get_async_client = AsyncMock(return_value=mock_async_client)

            result = await delete_schema_from_qdrant("ds1", "proj1")
            assert result is False
            # Verify that the exception was logged
            mock_logger.exception.assert_called_once()
