import asyncio
import json
from typing import Any

from langchain_core.documents import Document
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.core.log import logger
from app.models.data import DatasetDetails
from app.services.gopie.dataset_info import format_schema
from app.services.qdrant.qdrant_setup import initialize_qdrant_client
from app.services.qdrant.vector_store import add_document_to_vector_store
from app.utils.graph_utils.col_description_generator import (
    generate_column_descriptions,
)

background_tasks = set()


async def store_schema_in_qdrant(
    schema: Any,
    sample_data: Any,
    dataset_details: DatasetDetails,
    dataset_id: str,
    project_id: str,
) -> bool:
    try:
        formatted_schema = format_schema(
            schema, sample_data, project_id, dataset_id
        )

        formatted_schema["name"] = dataset_details.alias
        formatted_schema["dataset_name"] = dataset_details.name
        formatted_schema["dataset_description"] = dataset_details.description

        column_descriptions = await generate_column_descriptions(
            formatted_schema
        )

        for column in formatted_schema["columns"]:
            column["column_description"] = column_descriptions[
                column["column_name"]
            ]

        document = Document(
            page_content=json.dumps(formatted_schema, indent=2),
            metadata={
                "name": dataset_details.alias,
                "dataset_name": dataset_details.name,
                "dataset_description": dataset_details.description,
                "dataset_id": dataset_id,
                "project_id": project_id,
            },
        )

        task = asyncio.create_task(
            add_document_to_vector_store(document=document)
        )
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

        logger.debug("Schema indexing task created successfully")
        return True

    except Exception as e:
        logger.error(f"Error storing schema in Qdrant: {e!s}")
        return False


async def delete_schema_from_qdrant(
    dataset_id: str,
    project_id: str,
) -> bool:
    """
    Delete a schema from Qdrant vector database.

    Args:
        dataset_id: The ID of the dataset to delete.
        project_id: The ID of the project where the dataset belongs.

    Returns:
        bool: True if deletion was successful, False otherwise.
    """
    try:
        client = initialize_qdrant_client()

        search_result = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.project_id",
                        match=MatchValue(value=project_id),
                    ),
                    FieldCondition(
                        key="metadata.dataset_id",
                        match=MatchValue(value=dataset_id),
                    ),
                ]
            ),
            limit=1,
        )

        if not search_result[0]:
            logger.warning(
                f"Schema not found for project_id={project_id}, "
                f"dataset_id={dataset_id}"
            )
            return False

        point_to_delete = search_result[0][0]
        client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=[point_to_delete.id],
        )

        logger.debug(
            f"Successfully deleted schema for project_id={project_id}, "
            f"dataset_id={dataset_id}"
        )
        return True

    except Exception as e:
        logger.error(f"Error deleting schema from Qdrant: {e!s}")
        return False
