from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.routers.dataset_upload import delete_schema, upload_schema
from app.models.router import UploadSchemaRequest


class TestDatasetUpload:
    @pytest.fixture
    def upload_request(self):
        """
        Provides a sample UploadSchemaRequest with preset project and dataset IDs for use in upload schema tests.

        Returns:
            UploadSchemaRequest: An instance with test project and dataset IDs.
        """
        return UploadSchemaRequest(project_id="test_project_123", dataset_id="test_dataset_456")

    @pytest.fixture
    def delete_request(self):
        """
        Provides a sample UploadSchemaRequest for testing schema deletion operations.
        """
        return UploadSchemaRequest(project_id="test_project_123", dataset_id="test_dataset_456")

    @pytest.fixture
    def mock_dataset_details(self):
        """
        Return a mock dataset details object with predefined name, description, and schema attributes for use in tests.
        """
        return Mock(
            name="test_dataset",
            description="Test dataset description",
            schema={"columns": ["id", "name", "value"]},
        )

    @pytest.mark.asyncio
    async def test_upload_schema_success(self, upload_request, mock_dataset_details):
        """
        Test that uploading a schema succeeds when all dependent services return successful results.

        Verifies that the upload_schema function returns a success response and that all service dependencies are called with the expected arguments.
        """
        with (
            patch("app.api.v1.routers.dataset_upload.get_dataset_info") as mock_get_info,
            patch("app.api.v1.routers.dataset_upload.generate_summary") as mock_generate,
            patch("app.api.v1.routers.dataset_upload.store_schema_in_qdrant") as mock_store,
        ):

            mock_get_info.return_value = mock_dataset_details
            mock_generate.return_value = (
                {"schema": "test_schema"},
                {"sample": "test_data"},
            )
            mock_store.return_value = True

            result = await upload_schema(upload_request)

            assert result["success"] is True
            assert "successfully" in result["message"]
            mock_get_info.assert_called_once_with("test_dataset_456", "test_project_123")
            mock_generate.assert_called_once_with(mock_dataset_details.name)
            mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_schema_dataset_info_failure(self, upload_request):
        """
        Test that `upload_schema` raises an HTTP 500 error when dataset information retrieval fails.
        """
        with patch("app.api.v1.routers.dataset_upload.get_dataset_info") as mock_get_info:
            mock_get_info.side_effect = Exception("Dataset not found")

            with pytest.raises(HTTPException) as exc_info:
                await upload_schema(upload_request)

            assert exc_info.value.status_code == 500
            assert "Failed to process schema upload" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_schema_generate_schema_failure(
        self, upload_request, mock_dataset_details
    ):
        """
        Test that `upload_schema` raises an HTTP 500 error when schema generation fails.

        Simulates a failure in the `generate_summary` function and verifies that an HTTPException with status code 500 is raised.
        """
        with (
            patch("app.api.v1.routers.dataset_upload.get_dataset_info") as mock_get_info,
            patch("app.api.v1.routers.dataset_upload.generate_summary") as mock_generate,
        ):

            mock_get_info.return_value = mock_dataset_details
            mock_generate.side_effect = Exception("Schema generation failed")

            with pytest.raises(HTTPException) as exc_info:
                await upload_schema(upload_request)

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_upload_schema_store_failure(self, upload_request, mock_dataset_details):
        """
        Test that `upload_schema` raises an HTTP 500 error when storing the schema in the vector database fails.
        """
        with (
            patch("app.api.v1.routers.dataset_upload.get_dataset_info") as mock_get_info,
            patch("app.api.v1.routers.dataset_upload.generate_summary") as mock_generate,
            patch("app.api.v1.routers.dataset_upload.store_schema_in_qdrant") as mock_store,
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
            assert "Failed to store schema in vector database" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_schema_http_exception_passthrough(self, upload_request):
        """
        Test that an HTTPException raised during dataset info retrieval is propagated unchanged by the upload_schema function.
        """
        with patch("app.api.v1.routers.dataset_upload.get_dataset_info") as mock_get_info:
            original_exception = HTTPException(status_code=404, detail="Dataset not found")
            mock_get_info.side_effect = original_exception

            with pytest.raises(HTTPException) as exc_info:
                await upload_schema(upload_request)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Dataset not found"

    @pytest.mark.asyncio
    async def test_delete_schema_success(self, delete_request):
        """
        Test that deleting a schema with valid input returns a success response.

        Asserts that the deletion function is called with the correct dataset and project IDs, and that the response indicates successful deletion.
        """
        with patch("app.api.v1.routers.dataset_upload.delete_schema_from_qdrant") as mock_delete:
            mock_delete.return_value = True

            result = await delete_schema(delete_request)

            assert result["success"] is True
            assert "successfully" in result["message"]
            mock_delete.assert_called_once_with("test_dataset_456", "test_project_123")

    @pytest.mark.asyncio
    async def test_delete_schema_not_found(self, delete_request):
        """
        Test that deleting a schema returns a 404 HTTPException when the schema does not exist.

        Verifies that the `delete_schema` function raises an HTTPException with status code 404 and an appropriate error message when the underlying deletion service indicates the schema was not found.
        """
        with patch("app.api.v1.routers.dataset_upload.delete_schema_from_qdrant") as mock_delete:
            mock_delete.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await delete_schema(delete_request)

            assert exc_info.value.status_code == 404
            assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_schema_service_exception(self, delete_request):
        """
        Test that an HTTP 500 error is raised when an exception occurs during schema deletion.

        Verifies that if the underlying service raises an exception while deleting a schema, the API responds with a 500 status code and an appropriate error message.
        """
        with patch("app.api.v1.routers.dataset_upload.delete_schema_from_qdrant") as mock_delete:
            mock_delete.side_effect = Exception("Service error")

            with pytest.raises(HTTPException) as exc_info:
                await delete_schema(delete_request)

            assert exc_info.value.status_code == 500
            assert "Failed to delete schema" in str(exc_info.value.detail)
