from fastapi import APIRouter, HTTPException, status

from app.core.session import SingletonAiohttp
from app.models.router import UploadResponse, UploadSchemaRequest
from app.services.gopie.dataset_info import get_dataset_info
from app.services.gopie.generate_schema import generate_summary
from app.services.qdrant.schema_vectorization import (
    delete_schema_from_qdrant,
    store_schema_in_qdrant,
)

dataset_router = APIRouter()

http_session = SingletonAiohttp.get_aiohttp_client()


@dataset_router.post("/upload_schema", response_model=UploadResponse)
async def upload_schema(payload: UploadSchemaRequest):
    """
    Processes and index dataset schema.

    - `project_id`: The ID of the project where the dataset belongs.
    - `dataset_id`: The ID of the dataset.
    """
    try:
        project_id = payload.project_id
        dataset_id = payload.dataset_id

        dataset_details = await get_dataset_info(dataset_id, project_id)
        dataset_summary, sample_data = await generate_summary(dataset_details.name)

        success = await store_schema_in_qdrant(
            dataset_summary=dataset_summary,
            sample_data=sample_data,
            dataset_details=dataset_details,
            dataset_id=dataset_id,
            project_id=project_id,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store schema in vector database",
            )

        return {
            "success": True,
            "message": "Dataset information retrieved & stored successfully.",
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process schema upload: {e!s}",
        ) from e


@dataset_router.delete("/delete_schema", response_model=UploadResponse)
async def delete_schema(payload: UploadSchemaRequest):
    """
    Deletes dataset schema from the vector database.

    - `project_id`: The ID of the project where the dataset belongs.
    - `dataset_id`: The ID of the dataset to delete.
    """
    try:
        project_id = payload.project_id
        dataset_id = payload.dataset_id

        success = await delete_schema_from_qdrant(dataset_id, project_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schema not found or could not be deleted",
            )

        return {
            "success": True,
            "message": "Dataset schema deleted successfully.",
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete schema: {e!s}",
        ) from e
