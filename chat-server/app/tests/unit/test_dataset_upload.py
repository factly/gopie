"""Tests for dataset upload functionality."""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.routers.dataset_upload import upload_schema
from app.models.router import UploadSchemaRequest


class TestDatasetUpload:
    """Test cases for dataset upload functionality."""

    @pytest.fixture
    def upload_request(self):
        """Sample upload request."""
        return UploadSchemaRequest(
            project_id="test_project_123", dataset_id="test_dataset_456"
        )

    @pytest.fixture
    def mock_dataset_details(self):
        """Mock dataset details."""
        return Mock(
            name="test_dataset",
            description="Test dataset description",
            schema={"columns": ["id", "name", "value"]},
        )

    @pytest.mark.asyncio
    async def test_upload_schema_success(
        self, upload_request, mock_dataset_details
    ):
        """Test successful schema upload."""
        with (
            patch(
                "app.api.v1.routers.dataset_upload.get_dataset_info"
            ) as mock_get_info,
            patch(
                "app.api.v1.routers.dataset_upload.generate_schema"
            ) as mock_generate,
            patch(
                "app.api.v1.routers.dataset_upload.store_schema_in_qdrant"
            ) as mock_store,
        ):

            # Setup mocks
            mock_get_info.return_value = mock_dataset_details
            mock_generate.return_value = (
                {"schema": "test_schema"},
                {"sample": "test_data"},
            )
            mock_store.return_value = True

            # Execute
            result = await upload_schema(upload_request)

            # Assertions
            assert result["success"] is True
            assert "successfully" in result["message"]
            mock_get_info.assert_called_once_with(
                "test_dataset_456", "test_project_123"
            )
            mock_generate.assert_called_once_with(mock_dataset_details.name)
            mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_schema_dataset_info_failure(self, upload_request):
        """Test upload schema when dataset info retrieval fails."""
        with patch(
            "app.api.v1.routers.dataset_upload.get_dataset_info"
        ) as mock_get_info:
            mock_get_info.side_effect = Exception("Dataset not found")

            with pytest.raises(HTTPException) as exc_info:
                await upload_schema(upload_request)

            assert exc_info.value.status_code == 500
            assert "Failed to process schema upload" in str(
                exc_info.value.detail
            )

    @pytest.mark.asyncio
    async def test_upload_schema_generate_schema_failure(
        self, upload_request, mock_dataset_details
    ):
        """Test upload schema when schema generation fails."""
        with (
            patch(
                "app.api.v1.routers.dataset_upload.get_dataset_info"
            ) as mock_get_info,
            patch(
                "app.api.v1.routers.dataset_upload.generate_schema"
            ) as mock_generate,
        ):

            mock_get_info.return_value = mock_dataset_details
            mock_generate.side_effect = Exception("Schema generation failed")

            with pytest.raises(HTTPException) as exc_info:
                await upload_schema(upload_request)

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_upload_schema_store_failure(
        self, upload_request, mock_dataset_details
    ):
        """Test upload schema when vector store storage fails."""
        with (
            patch(
                "app.api.v1.routers.dataset_upload.get_dataset_info"
            ) as mock_get_info,
            patch(
                "app.api.v1.routers.dataset_upload.generate_schema"
            ) as mock_generate,
            patch(
                "app.api.v1.routers.dataset_upload.store_schema_in_qdrant"
            ) as mock_store,
        ):

            mock_get_info.return_value = mock_dataset_details
            mock_generate.return_value = (
                {"schema": "test"},
                {"sample": "data"},
            )
            mock_store.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await upload_schema(upload_request)

            assert exc_info.value.status_code == 500
            assert "Failed to store schema in vector database" in str(
                exc_info.value.detail
            )

    @pytest.mark.asyncio
    async def test_upload_schema_http_exception_passthrough(
        self, upload_request
    ):
        """Test that HTTPExceptions are passed through without wrapping."""
        with patch(
            "app.api.v1.routers.dataset_upload.get_dataset_info"
        ) as mock_get_info:
            original_exception = HTTPException(
                status_code=404, detail="Dataset not found"
            )
            mock_get_info.side_effect = original_exception

            with pytest.raises(HTTPException) as exc_info:
                await upload_schema(upload_request)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Dataset not found"
