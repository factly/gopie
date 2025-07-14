import pytest
from unittest.mock import Mock, patch, AsyncMock
from langchain_core.documents import Document
from typing import Union, cast
from langchain_openai import OpenAIEmbeddings

from app.services.qdrant.vector_store import (
    add_document_to_vector_store,
    perform_similarity_search,
)
from app.services.qdrant.schema_search import search_schemas
from app.services.qdrant.schema_vectorization import (
    store_schema_in_qdrant,
    delete_schema_from_qdrant,
)


class TestVectorStore:
    @pytest.fixture
    def mock_document(self):
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
        embeddings = Mock()
        embeddings.embed_query = Mock(return_value=[0.1, 0.2, 0.3])
        return embeddings

    @pytest.mark.asyncio
    async def test_add_document_to_vector_store(self, mock_document):
        mock_vector_store = AsyncMock()

        with (
            patch("app.services.qdrant.vector_store.QdrantSetup") as mock_qdrant_setup_class,
            patch("app.services.qdrant.vector_store.get_model_provider") as mock_get_model_provider,
        ):
            mock_model_provider = Mock()
            mock_embeddings = Mock()
            mock_model_provider.get_embeddings_model.return_value = mock_embeddings
            mock_get_model_provider.return_value = mock_model_provider

            mock_qdrant_setup_class.get_vector_store.return_value = mock_vector_store
            mock_qdrant_setup_class.get_document_id.return_value = "doc_id_123"

            await add_document_to_vector_store(mock_document)

            mock_qdrant_setup_class.get_vector_store.assert_called_once_with(mock_embeddings)
            mock_qdrant_setup_class.get_document_id.assert_called_once_with("proj1", "ds1")
            mock_vector_store.aadd_documents.assert_called_once_with(
                documents=[mock_document], ids=["doc_id_123"]
            )

    @pytest.mark.asyncio
    async def test_perform_similarity_search_success(self):
        mock_vector_store = AsyncMock()
        mock_vector_store.asimilarity_search.return_value = [
            Document(page_content="result 1"),
            Document(page_content="result 2"),
        ]

        results = await perform_similarity_search(mock_vector_store, "test query", top_k=5)

        assert len(results) == 2
        mock_vector_store.asimilarity_search.assert_called_once_with("test query", k=5, filter=None)

    @pytest.mark.asyncio
    async def test_perform_similarity_search_with_filter(self):
        mock_vector_store = AsyncMock()
        mock_vector_store.asimilarity_search.return_value = [
            Document(page_content="filtered result")
        ]

        query_filter = Mock()
        results = await perform_similarity_search(
            mock_vector_store, "test query", query_filter=query_filter, top_k=3
        )

        assert len(results) == 1
        mock_vector_store.asimilarity_search.assert_called_once_with(
            "test query", k=3, filter=query_filter
        )

    @pytest.mark.asyncio
    async def test_perform_similarity_search_fallback_on_error(self):
        mock_vector_store = AsyncMock()
        # First call with filter raises exception, second without filter succeeds
        mock_vector_store.asimilarity_search.side_effect = [
            Exception("Filter error"),
            [Document(page_content="fallback result")],
        ]

        query_filter = Mock()
        results = await perform_similarity_search(
            mock_vector_store, "test query", query_filter=query_filter, top_k=3
        )

        assert len(results) == 1
        assert mock_vector_store.asimilarity_search.call_count == 2

    @pytest.mark.asyncio
    async def test_perform_similarity_search_raises_on_unfiltered_error(self):
        mock_vector_store = AsyncMock()
        mock_vector_store.asimilarity_search.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await perform_similarity_search(mock_vector_store, "test query")


class TestSchemaSearch:
    @pytest.fixture
    def mock_embeddings(self):
        embeddings = Mock(spec=OpenAIEmbeddings)
        embeddings.embed_query = Mock(return_value=[0.1, 0.2, 0.3])
        return cast(OpenAIEmbeddings, embeddings)

    @pytest.mark.asyncio
    async def test_search_schemas_success(self, mock_embeddings):
        mock_documents = [
            Document(
                page_content="schema1",
                metadata={
                    "name": "test1",
                    "dataset_name": "test1",  # Required field
                    "dataset_description": "Test dataset 1",
                    "project_id": "proj1",
                    "dataset_id": "ds1",
                    "columns": [],
                },
            ),
            Document(
                page_content="schema2",
                metadata={
                    "name": "test2",
                    "dataset_name": "test2",  # Required field
                    "dataset_description": "Test dataset 2",
                    "project_id": "proj2",
                    "dataset_id": "ds2",
                    "columns": [],
                },
            ),
        ]

        with (
            patch("app.services.qdrant.schema_search.QdrantSetup") as mock_qdrant_setup_class,
            patch(
                "app.services.qdrant.schema_search.perform_similarity_search"
            ) as mock_perform_search,
        ):
            mock_vector_store = AsyncMock()
            mock_qdrant_setup_class.get_vector_store.return_value = mock_vector_store
            mock_perform_search.return_value = mock_documents

            schemas = await search_schemas(user_query="test query", embeddings=mock_embeddings)

            assert len(schemas) == 2
            assert schemas[0].name == "test1"
            assert schemas[1].name == "test2"

    @pytest.mark.asyncio
    async def test_search_schemas_with_filters(self, mock_embeddings):
        mock_document = Document(
            page_content="filtered schema",
            metadata={
                "name": "filtered_test",
                "dataset_name": "filtered_test",  # Required field
                "dataset_description": "Filtered test dataset",
                "project_id": "proj1",
                "dataset_id": "ds1",
                "columns": [],
            },
        )

        with (
            patch("app.services.qdrant.schema_search.QdrantSetup") as mock_qdrant_setup_class,
            patch(
                "app.services.qdrant.schema_search.perform_similarity_search"
            ) as mock_perform_search,
        ):
            mock_vector_store = AsyncMock()
            mock_qdrant_setup_class.get_vector_store.return_value = mock_vector_store
            mock_perform_search.return_value = [mock_document]

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
        with (
            patch("app.services.qdrant.schema_search.QdrantSetup") as mock_qdrant_setup_class,
            patch(
                "app.services.qdrant.schema_search.perform_similarity_search"
            ) as mock_perform_search,
        ):
            mock_vector_store = AsyncMock()
            mock_qdrant_setup_class.get_vector_store.return_value = mock_vector_store
            mock_perform_search.side_effect = Exception("Search error")

            schemas = await search_schemas(user_query="test query", embeddings=mock_embeddings)
            assert schemas == []

    @pytest.mark.asyncio
    async def test_search_schemas_empty_results(self, mock_embeddings):
        with (
            patch("app.services.qdrant.schema_search.QdrantSetup") as mock_qdrant_setup_class,
            patch(
                "app.services.qdrant.schema_search.perform_similarity_search"
            ) as mock_perform_search,
        ):
            mock_vector_store = AsyncMock()
            mock_qdrant_setup_class.get_vector_store.return_value = mock_vector_store
            mock_perform_search.return_value = []

            schemas = await search_schemas(user_query="test query", embeddings=mock_embeddings)
            assert schemas == []


class TestSchemaVectorization:
    @pytest.mark.asyncio
    async def test_store_schema_in_qdrant_success(self):
        # Create mock data with proper typing for SQL_RESPONSE_TYPE
        dataset_summary = Mock()
        sample_data: list[dict[str, Union[str, int, float, None]]] = [
            {"col1": "value1", "col2": 42, "col3": 3.14, "col4": None}
        ]
        dataset_details = Mock()

        with (
            patch(
                "app.services.qdrant.schema_vectorization.create_dataset_schema"
            ) as mock_create_schema,
            patch(
                "app.services.qdrant.schema_vectorization.generate_column_descriptions"
            ) as mock_generate_desc,
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
            mock_generate_desc.return_value = {"col1": "Column 1 description"}
            mock_format_schema.return_value = "formatted schema content"
            mock_add_document.return_value = None

            result = await store_schema_in_qdrant(
                dataset_summary, sample_data, dataset_details, "ds1", "proj1"
            )

            assert result is True
            mock_create_schema.assert_called_once()
            mock_add_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_schema_in_qdrant_failure(self):
        dataset_summary = Mock()
        sample_data: list[dict[str, Union[str, int, float, None]]] = [
            {"col1": "value1", "col2": 42}
        ]
        dataset_details = Mock()

        with (
            patch(
                "app.services.qdrant.schema_vectorization.create_dataset_schema"
            ) as mock_create_schema,
        ):
            mock_create_schema.side_effect = Exception("Storage error")

            result = await store_schema_in_qdrant(
                dataset_summary, sample_data, dataset_details, "ds1", "proj1"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_schema_from_qdrant_success(self):
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
        with (
            patch(
                "app.services.qdrant.schema_vectorization.QdrantSetup"
            ) as mock_qdrant_setup_class,
        ):
            mock_async_client = Mock()
            mock_async_client.delete = AsyncMock(side_effect=Exception("Delete error"))
            mock_qdrant_setup_class.get_async_client = AsyncMock(return_value=mock_async_client)

            result = await delete_schema_from_qdrant("ds1", "proj1")
            assert result is False
