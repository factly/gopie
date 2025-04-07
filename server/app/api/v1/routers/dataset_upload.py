import json
import logging

from app.core.config import settings
from app.core.session import SingletonAiohttp
from app.models.data import UploadResponse, UploadSchemaRequest
from app.models.schema import DatasetSchema
from app.services.qdrant.schema_vectorization import store_schema_in_qdrant
from fastapi import APIRouter, HTTPException

dataset_router = APIRouter()

http_session = SingletonAiohttp.get_aiohttp_client()

PREFETCH_API_URL = settings.HUNTING_API_ENDPOINT + "/api/v1/prefetch"
PROFILE_API_URL = settings.HUNTING_API_ENDPOINT + "/api/v1/profile/description"


@dataset_router.post("/upload_schema", response_model=UploadResponse)
async def upload_schema(payload: UploadSchemaRequest):
    try:
        project_id = payload.project_id
        dataset_id = payload.dataset_id
        file_path = payload.file_path

        logging.info(
            f"Processing schema upload for dataset {dataset_id} in project {project_id}"
        )

        payloads = {
            "urls": [file_path],
            "minimal": True,
            "samples_to_fetch": 10,
            "trigger_id": "",
        }
        headers = {"accept": "application/json", "Content-Type": "application/json"}

        response = await http_session.post(
            PREFETCH_API_URL, json=payloads, headers=headers
        )

        if response.status != 200:
            raise HTTPException(response.status, await response.text())

        payloads = {
            "source": file_path,
            "samples_to_show": 10,
        }

        fetched_dataset_schema = await http_session.get(
            PROFILE_API_URL, params=payloads, headers=headers
        )

        if fetched_dataset_schema.status != 200:
            raise HTTPException(
                fetched_dataset_schema.status, await fetched_dataset_schema.text()
            )

        dataset_schema = await fetched_dataset_schema.json()

        transformed_schema: DatasetSchema = {
            "name": file_path.split("/")[-1],
            "dataset_id": dataset_id,
            "file_path": file_path,
            "project_id": project_id,
            "analysis": dataset_schema["analysis"],
            "row_count": dataset_schema["table"]["n"],
            "col_count": dataset_schema["table"]["n_var"],
            "columns": [
                {
                    "name": col,
                    "description": "",
                    "type": dataset_schema["variables"][col]["type"],
                    "sample_values": dataset_schema["samples"][0]["data"][col] if dataset_schema["samples"] else {},
                    "non_null_count": dataset_schema["variables"][col]["n"] - dataset_schema["variables"][col]["n_missing"]
                }
                for col in dataset_schema["columns"]
            ]
        }

        success = store_schema_in_qdrant(transformed_schema)
        if not success:
            raise HTTPException(500, "Failed to store schema in vector database")

        return {
            "success": True,
            "message": "Dataset information retrieved and stored successfully.",
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error processing schema upload: {str(e)}")
        raise HTTPException(500, str(e))
