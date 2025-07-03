import json

from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.core.log import logger
from app.services.qdrant.qdrant_setup import initialize_qdrant_client


async def get_schema_from_qdrant(dataset_id: str) -> dict:
    """
    Get the schema of a specific table from Qdrant database.

    Args:
        dataset_id: The id of the dataset to retrieve schema for.

    Returns:
        A dictionary with schema information for the provided dataset id.
    """
    try:
        client = initialize_qdrant_client()

        filter_conditions = []

        if dataset_id:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.dataset_id",
                    match=MatchValue(value=dataset_id),
                )
            )

        if filter_conditions:
            search_result = client.scroll(
                collection_name=settings.QDRANT_COLLECTION,
                scroll_filter=Filter(should=filter_conditions),
                limit=1,
            )

        if not search_result[0]:
            return {
                "error": f"Dataset '{dataset_id}' not found in the database."
            }

        payload = search_result[0][0].payload
        if not payload:
            return {
                "error": "Schema information not available for this dataset."
            }

        schema = json.loads(payload.get("page_content", "{}"))

        return schema

    except Exception as e:
        return {"error": f"Error retrieving schema from Qdrant: {e!s}"}


def get_schema_by_dataset_ids(dataset_ids: list[str]) -> list[dict]:
    """
    Get the schema of a list of datasets from Qdrant database.

    Args:
        dataset_ids: List of dataset IDs to retrieve schemas for.

    Returns:
        List of schema dictionaries for the provided dataset IDs.
    """
    if not dataset_ids:
        return []

    try:
        client = initialize_qdrant_client()

        filter_conditions = []
        for dataset_id in dataset_ids:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.dataset_id",
                    match=MatchValue(value=dataset_id),
                )
            )

        search_result = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=Filter(should=filter_conditions),
            limit=len(dataset_ids),
        )

        schemas = []
        if search_result[0]:
            for point in search_result[0]:
                payload = point.payload
                if payload:
                    try:
                        schema = json.loads(payload.get("page_content", "{}"))
                        schemas.append(schema)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing schema JSON: {e}")
                        continue

        return schemas

    except Exception as e:
        logger.error(f"Error retrieving schemas from Qdrant: {e}")
        return []
