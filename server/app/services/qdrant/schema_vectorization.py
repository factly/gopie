import asyncio
import json
import logging
from typing import Any

from app.models.data import Dataset_details
from app.services.dataset_info import format_schema
from app.services.qdrant.vector_store import add_documents_to_vector_store
from langchain_core.documents import Document


def store_schema_in_qdrant(
    schema: Any,
    dataset_details: Dataset_details,
    dataset_id: str,
    project_id: str,
    file_path: str,
) -> bool:
    try:
        formatted_schema = format_schema(schema, project_id, dataset_id, file_path)

        formatted_schema["name"] = dataset_details.alias
        formatted_schema["dataset_name"] = dataset_details.name
        formatted_schema["dataset_description"] = dataset_details.description

        document = Document(
            page_content=json.dumps(formatted_schema, indent=2),
            metadata={
                "name": dataset_details.alias,
                "dataset_name": dataset_details.name,
                "dataset_description": dataset_details.description,
                "dataset_id": dataset_id,
                "project_id": project_id,
                "file_path": file_path,
            },
        )

        asyncio.create_task(add_documents_to_vector_store(documents=[document]))

        logging.info("Schema indexing task created successfully")
        return True

    except Exception as e:
        logging.error(f"Error storing schema in Qdrant: {str(e)}")
        return False
