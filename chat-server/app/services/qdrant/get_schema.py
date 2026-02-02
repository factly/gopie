from typing import Optional

from langsmith import traceable
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.core.log import custom_logger as logger
from app.models.schema import DatasetSchema
from app.services.qdrant.qdrant_setup import QdrantSetup


@traceable(run_type="tool", name="get_schema_from_qdrant")
async def get_schema_from_qdrant(
    dataset_id: str, org_id: str | None = None
) -> Optional[DatasetSchema]:
    """
    Get the schema of a specific table from Qdrant database.

    Args:
        dataset_id: The id of the dataset to retrieve schema for.
        org_id: The id of the organization to retrieve schema for.
    Returns:
        A DatasetSchema object with schema information.
    """
    try:
        client = await QdrantSetup.get_async_client(settings.QDRANT_COLLECTION)

        filter_conditions = []

        if dataset_id:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.dataset_id",
                    match=MatchValue(value=dataset_id),
                )
            )

        if org_id:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.org_id",
                    match=MatchValue(value=org_id),
                )
            )

        if filter_conditions:
            search_result = await client.scroll(
                collection_name=settings.QDRANT_COLLECTION,
                scroll_filter=Filter(should=filter_conditions),
                limit=1,
            )

        if not search_result[0] or not search_result[0][0]:
            return None

        payload = search_result[0][0].payload
        if not payload:
            return None

        metadata = payload.get("metadata", {})
        dataset_schema = DatasetSchema(**metadata)

        return dataset_schema

    except Exception as e:
        logger.exception(f"Error retrieving schema from Qdrant: {e!s}")
        return None


@traceable(run_type="tool", name="get_schema_by_dataset_ids")
async def get_schema_by_dataset_ids(
    dataset_ids: list[str] | None = None,
    org_id: str | None = None,
) -> list[DatasetSchema]:
    """
    Get the schema of a list of datasets from Qdrant database.

    Args:
        dataset_ids: List of dataset IDs to retrieve schemas for.
        org_id: The id of the organization to retrieve schema for.
    Returns:
        List of schema objects for the provided dataset IDs.
    """
    if not dataset_ids:
        return []

    try:
        client = await QdrantSetup.get_async_client(settings.QDRANT_COLLECTION)

        filter_conditions = []
        for dataset_id in dataset_ids:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.dataset_id",
                    match=MatchValue(value=dataset_id),
                )
            )

        if org_id:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.org_id",
                    match=MatchValue(value=org_id),
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
                        metadata = payload.get("metadata", {})
                        dataset_schema = DatasetSchema(**metadata)
                        schemas.append(dataset_schema)
                    except Exception as e:
                        logger.exception(f"Error creating schema from metadata: {e}")
                        continue

        return schemas

    except Exception as e:
        logger.exception(f"Error retrieving schemas from Qdrant: {e}")
        return []


@traceable(run_type="tool", name="get_project_schemas")
async def get_project_schemas(
    project_id: str, limit: int = 5, org_id: str | None = None
) -> list[DatasetSchema]:
    """
    Get all dataset schemas for a project from Qdrant database.

    Args:
        project_id: Project ID to retrieve schemas for.
        limit: Maximum number of datasets to retrieve.
        org_id: The id of the organization to retrieve schema for.
    Returns:
        List of schema objects for all datasets in the provided project.
    """
    try:
        client = await QdrantSetup.get_async_client(settings.QDRANT_COLLECTION)

        filter_conditions = []
        filter_conditions.append(
            FieldCondition(
                key="metadata.project_id",
                match=MatchValue(value=project_id),
            )
        )

        if org_id:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.org_id",
                    match=MatchValue(value=org_id),
                )
            )

        points, _ = await client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=Filter(must=filter_conditions),
            limit=limit,
        )

        schemas = []
        for point in points:
            payload = point.payload
            if payload:
                try:
                    metadata = payload.get("metadata", {})
                    dataset_schema = DatasetSchema(**metadata)
                    schemas.append(dataset_schema)
                except Exception as e:
                    logger.warning(f"Error creating schema from metadata: {e}")
                    continue

        return schemas

    except Exception as e:
        logger.exception(f"Error retrieving schemas from Qdrant: {e}")
        return []
