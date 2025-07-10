from langchain_core.documents import Document

from app.core.config import settings
from app.core.log import logger
from app.models.data import DatasetDetails
from app.models.schema import DatasetSummary
from app.services.gopie.dataset_info import (
    create_dataset_schema,
    format_schema_for_embedding,
)
from app.services.gopie.sql_executor import SQL_RESPONSE_TYPE
from app.services.qdrant.qdrant_setup import QdrantSetup
from app.services.qdrant.vector_store import add_document_to_vector_store
from app.utils.graph_utils.col_description_generator import (
    generate_column_descriptions,
)


async def store_schema_in_qdrant(
    dataset_summary: DatasetSummary,
    sample_data: SQL_RESPONSE_TYPE,
    dataset_details: DatasetDetails,
    dataset_id: str,
    project_id: str,
) -> bool:
    try:
        dataset_schema = create_dataset_schema(
            dataset_summary=dataset_summary,
            sample_data=sample_data,
            project_id=project_id,
            dataset_id=dataset_id,
            dataset_details=dataset_details,
        )

        column_descriptions = await generate_column_descriptions(
            dataset_schema
        )

        for column in dataset_schema.columns:
            column.column_description = column_descriptions[column.column_name]

        document = Document(
            page_content=format_schema_for_embedding(dataset_schema),
            metadata={
                **dataset_schema.model_dump(exclude_defaults=True),
            },
        )

        await add_document_to_vector_store(document=document)

        logger.debug("Schema indexing task created successfully")
        return True

    except Exception as e:
        logger.exception(
            f"Error storing schema in Qdrant: {e!s}",
            exc_info=True,
            stack_info=True,
        )
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
        client = await QdrantSetup.get_async_client()
        document_id = QdrantSetup.get_document_id(project_id, dataset_id)
        await client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=[document_id],
        )

        logger.debug(
            f"Successfully deleted schema for project_id={project_id}, "
            f"dataset_id={dataset_id}"
        )
        return True

    except Exception as e:
        logger.error(f"Error deleting schema from Qdrant: {e!s}")
        return False
