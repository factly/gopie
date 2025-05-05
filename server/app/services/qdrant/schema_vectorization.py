import asyncio
import json
import logging
from typing import Any

from langchain_core.documents import Document

from app.models.data import DatasetDetails
from app.services.dataset_info import format_schema
from app.services.qdrant.vector_store import add_documents_to_vector_store

background_tasks = set()


def store_schema_in_qdrant(
    schema: Any,
    sample_data: Any,
    dataset_details: DatasetDetails,
    dataset_id: str,
    project_id: str,
    file_path: str,
) -> bool:
    try:
        formatted_schema = format_schema(
            schema, sample_data, project_id, dataset_id, file_path
        )

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

        task = asyncio.create_task(
            add_documents_to_vector_store(documents=[document])
        )
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

        logging.info("Schema indexing task created successfully")
        return True

    except Exception as e:
        logging.error(f"Error storing schema in Qdrant: {e!s}")
        return False
