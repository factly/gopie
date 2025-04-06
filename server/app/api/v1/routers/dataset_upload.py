import json
import logging

import aiohttp
from app.core.config import settings
from app.models.data import UploadResponse, UploadSchemaRequest
from fastapi import APIRouter, HTTPException

dataset_router = APIRouter()


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

        async with aiohttp.ClientSession() as session:
            async with session.post(
                settings.HUNTING_API_URL, json=payloads, headers=headers
            ) as response:
                if response.status >= 400:
                    response_text = await response.text()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Prefetch API error: {response.status} - {response_text[:100]}",
                    )

                try:
                    response_data = await response.json()
                    print(response_data)
                    logging.debug("Successfully processed schema data")
                except json.JSONDecodeError:
                    response_text = await response.text()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Invalid response from prefetch API: {response_text[:100]}...",
                    )

        return {
            "success": True,
            "message": "Dataset information retrieved successfully.",
        }
    except HTTPException:
        raise
    except aiohttp.ClientError as e:
        logging.error(f"Connection error with prefetch API: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error connecting to prefetch API: {str(e)}"
        )
    except Exception as e:
        logging.error(f"Unexpected error during schema upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
