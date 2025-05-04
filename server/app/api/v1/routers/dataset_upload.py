from fastapi import APIRouter, HTTPException, status

from app.core.session import SingletonAiohttp
from app.models.router import UploadResponse, UploadSchemaRequest
from app.services.dataset_info import get_dataset_info
from app.services.qdrant.schema_vectorization import store_schema_in_qdrant
from app.services.schema_fetcher import (
    fetch_dataset_schema,
    initiate_schema_generation,
)

dataset_router = APIRouter()

http_session = SingletonAiohttp.get_aiohttp_client()


@dataset_router.post("/upload_schema", response_model=UploadResponse)
async def upload_schema(payload: UploadSchemaRequest):
    """
    Processes and index dataset schema.

    - `project_id`: The ID of the project where the dataset belongs.
    - `dataset_id`: The ID of the dataset.
    - `file_path`: The S3 path of the dataset file.
    """
    try:
        project_id = payload.project_id
        dataset_id = payload.dataset_id
        file_path = payload.file_path

        task_data = await initiate_schema_generation(file_path)
        dataset_schema = await fetch_dataset_schema(file_path, task_data)
        dataset_details = await get_dataset_info(dataset_id, project_id)

        success = store_schema_in_qdrant(
            dataset_schema, dataset_details, dataset_id, project_id, file_path
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
