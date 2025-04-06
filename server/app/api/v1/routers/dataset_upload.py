from fastapi import APIRouter, HTTPException
from app.models.data import UploadResponse, UploadSchemaRequest
from app.core.config import settings
import requests
import json

dataset_router = APIRouter()


@dataset_router.post("/upload_schema", response_model=UploadResponse)
async def upload_schema(payload: UploadSchemaRequest):
    print(f"Received request: {payload}")
    try:
        project_id = payload.project_id
        dataset_id = payload.dataset_id
        file_path = payload.file_path

        print("Received request to get dataset info")
        print(f"Project ID: {project_id}")
        print(f"Dataset ID: {dataset_id}")
        print(f"File Path: {file_path}")

        payloads = {
            "urls": [file_path],
            "minimal": True,
            "samples_to_fetch": 10,
            "trigger_id": "test_trigger_id"
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(settings.HUNTING_API_URL, json=payloads, headers=headers)

        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response content: {response.text}")

        response.raise_for_status()

        try:
            response_data = response.json()
            print(f"Response data: {response_data}")
        except json.JSONDecodeError:
            print(f"Invalid JSON response: {response.text}")
            raise HTTPException(status_code=500, detail=f"Invalid response from prefetch API: {response.text[:100]}...")

        return {
            "success": True,
            "message": f"Dataset information retrieved successfully.",
        }
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        error_detail = f"Prefetch API error: {str(e)}"
        try:
            error_text = response.text[:200] if response and hasattr(response, 'text') else "No response text"
            error_detail += f" - Response: {error_text}"
        except:
            pass
        raise HTTPException(status_code=500, detail=error_detail)
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"Error connecting to prefetch API: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))