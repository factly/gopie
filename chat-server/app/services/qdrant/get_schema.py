import json
from typing import Optional

from langsmith import traceable
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.core.log import logger
from app.models.schema import DatasetSchema
from app.services.qdrant.qdrant_setup import QdrantSetup


@traceable(run_type="tool", name="get_schema_from_qdrant")
async def get_schema_from_qdrant(dataset_id: str) -> Optional[DatasetSchema]:
    """
    Get the schema of a specific table from Qdrant database.

    Args:
        dataset_id: The id of the dataset to retrieve schema for.
    Returns:
        A DatasetSchema object with schema information.
    """
    try:
        client = await QdrantSetup.get_async_client()

        filter_conditions = []

        if dataset_id:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.dataset_id",
                    match=MatchValue(value=dataset_id),
                )
            )

        if filter_conditions:
            search_result = await client.scroll(
                collection_name=settings.QDRANT_COLLECTION,
                scroll_filter=Filter(should=filter_conditions),
                limit=1,
            )

        if not search_result[0]:
            return None

        payload = search_result[0][0].payload
        if not payload:
            return None

        dataset_schema = DatasetSchema(**payload)

        return dataset_schema

    except Exception as e:
        logger.error(f"Error retrieving schema from Qdrant: {e!s}")
        return None


@traceable(run_type="tool", name="get_schema_by_dataset_ids")
async def get_schema_by_dataset_ids(
    dataset_ids: list[str] | None = None,
) -> list[DatasetSchema]:
    """
    Get the schema of a list of datasets from Qdrant database.

    Args:
        dataset_ids: List of dataset IDs to retrieve schemas for.

    Returns:
        List of schema objects for the provided dataset IDs.
    """
    if not dataset_ids:
        return []

    try:
        client = await QdrantSetup.get_async_client()

        filter_conditions = []
        for dataset_id in dataset_ids:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.dataset_id",
                    match=MatchValue(value=dataset_id),
                )
            )

        search_result = await client.scroll(
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
                        dataset_schema = DatasetSchema(**payload)
                        schemas.append(dataset_schema)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing schema JSON: {e}")
                        continue

        return schemas

    except Exception as e:
        logger.error(f"Error retrieving schemas from Qdrant: {e}")
        return []
