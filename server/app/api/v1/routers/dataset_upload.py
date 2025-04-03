from fastapi import APIRouter, HTTPException
import os

from server.app.models.data import UploadResponse
from server.app.services.qdrant.qdrant_setup import initialize_qdrant_client, setup_vector_store
from server.app.services.qdrant.csv_processing import csv_metadata_to_document
from server.app.models.types import DatasetSchema
from uuid import uuid4

dataset_router = APIRouter()

def store_schema(file_name: str, schema: DatasetSchema):
    """Store schema in Qdrant without uploading the file."""
    try:
        client = initialize_qdrant_client()
        vector_store = setup_vector_store(client)

        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

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
            document = csv_metadata_to_document(schema)
            vector_store.add_documents(documents=[document], ids=[str(uuid4())])
            print(f"Schema for {file_name} vectorized successfully")
        else:
            print(f"Schema for {file_name} already exists in vector store, skipping vectorization")

        return True
    except Exception as e:
        print(f"Error processing schema {file_name}: {str(e)}")
        return False

@dataset_router.post("/index/schema", response_model=UploadResponse)
async def index_dataset_schema(
    file_name: str,
    schema: DatasetSchema
):
    """
    Index the schema of a dataset.

    Args:
        file_name: Name of the file including extension
        schema: The schema/metadata of the dataset

    Returns:
        Status of the schema indexing operation
    """
    try:
        table_name = os.path.splitext(file_name)[0]

        success = store_schema(file_name, schema)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store schema in vector database")

        return {
            "success": True,
            "message": f"Schema for {file_name} indexed successfully.",
            "dataset_name": table_name,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))