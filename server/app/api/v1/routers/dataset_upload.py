from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
import os
import shutil

from server.app.models.data import UploadResponse
from server.app.services.dataset_profiling import profile_dataset
from server.app.services.qdrant.qdrant_setup import initialize_qdrant_client, setup_vector_store
from server.app.services.qdrant.csv_processing import extract_csv_metadata, csv_metadata_to_document
from uuid import uuid4

dataset_router = APIRouter()

def process_upload_dataset(file_path: str, dataset_name: str):
    """Process the uploaded dataset: extract metadata, vectorize, and profile it."""
    try:
        metadata = extract_csv_metadata(file_path)

        client = initialize_qdrant_client()
        vector_store = setup_vector_store(client)

        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

        file_name = os.path.basename(file_path)
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="metadata.file_name",
                    match=MatchValue(value=file_name)
                )
            ]
        )

        count_response = client.count(
            collection_name="dataset_collection",
            count_filter=filter_condition
        )

        if count_response.count == 0:
            document = csv_metadata_to_document(metadata)
            vector_store.add_documents(documents=[document], ids=[str(uuid4())])
            print(f"Dataset {dataset_name} vectorized successfully")
        else:
            print(f"Dataset {dataset_name} already exists in vector store, skipping vectorization")

        profile_dataset(metadata)

        print(f"Dataset {dataset_name} processed successfully")
    except Exception as e:
        print(f"Error processing dataset {dataset_name}: {str(e)}")

@dataset_router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload a dataset file.

    The file will be stored, profiled, and vectorized for semantic search.

    Args:
        dataset_name: Name of the dataset (used only for identification, not for storage path)
        file: The dataset file (CSV, Parquet, or JSON)

    Returns:
        Status of the upload operation
    """
    try:
        from server.app.core.config import settings

        if file.filename is None:
            raise HTTPException(status_code=400, detail="No file provided or filename is empty")

        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.csv', '.parquet', '.json']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_extension}. Only CSV, Parquet, and JSON are supported."
            )

        table_name = os.path.splitext(file.filename)[0]
        file_path = os.path.join(settings.DATA_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file_extension == '.csv':
            background_tasks.add_task(process_upload_dataset, file_path, table_name)

        return {
            "success": True,
            "message": f"Dataset {file.filename} uploaded successfully and processing started.",
            "dataset_name": table_name,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))