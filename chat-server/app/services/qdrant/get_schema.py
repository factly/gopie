import json

from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
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
