from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
import os
import shutil

from server.app.models.data import UploadResponse
from server.app.services.dataset_profiling import profile_dataset
from server.app.services.qdrant.vector_store import vectorize_dataset

data_router = APIRouter()

@data_router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    dataset_name: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload a dataset file.

    The file will be stored, profiled, and vectorized for semantic search.

    Args:
        dataset_name: Name of the dataset
        file: The dataset file (CSV, Parquet, or JSON)

    Returns:
        Status of the upload operation
    """
    try:
        from server.app.core.config import settings

        if file.filename is None:
            raise HTTPException(status_code=400, detail="No file provided or filename is empty")

        dataset_dir = os.path.join(settings.DATA_DIR, dataset_name)
        os.makedirs(dataset_dir, exist_ok=True)

        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.csv', '.parquet', '.json']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_extension}. Only CSV, Parquet, and JSON are supported."
            )

        table_name = os.path.splitext(file.filename)[0]
        file_path = os.path.join(dataset_dir, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # background_tasks.add_task(profile_dataset(), dataset_name, file_path)

        return {
            "success": True,
            "message": f"Dataset {file.filename} uploaded successfully and processing started.",
            "dataset_name": dataset_name,
            "table_name": table_name,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))