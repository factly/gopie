import logging

from app.core.session import SingletonAiohttp
from app.models.data import UploadResponse, UploadSchemaRequest
from app.services.dataset_info import get_dataset_info
from app.services.qdrant.schema_vectorization import store_schema_in_qdrant
from app.services.schema_fetcher import fetch_dataset_schema, initiate_schema_generation
from fastapi import APIRouter, HTTPException, status

dataset_router = APIRouter()

http_session = SingletonAiohttp.get_aiohttp_client()


@dataset_router.post("/upload_schema", response_model=UploadResponse)
async def upload_schema(payload: UploadSchemaRequest):
    try:
        project_id = payload.project_id
        dataset_id = payload.dataset_id
        file_path = payload.file_path

        logging.info(
            f"Processing schema upload for dataset {dataset_id} in project {project_id}"
        )

        task_data = await initiate_schema_generation(file_path)
        logging.info(f"Schema generation initiated for {file_path}")

        dataset_schema = await fetch_dataset_schema(file_path, task_data)
        logging.info(f"Schema fetched successfully for {file_path}")

        dataset_details = await get_dataset_info(dataset_id, project_id)
        logging.info(f"Dataset info retrieved for dataset {dataset_id}")

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
            "message": "Dataset information retrieved and stored successfully.",
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Unexpected error processing schema upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process schema upload: {str(e)}",
        )
