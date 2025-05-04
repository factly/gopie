from typing import Any

from langchain_core.tools import tool
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.services.qdrant.qdrant_setup import initialize_qdrant_client


@tool
async def get_table_schema(dataset_name: str) -> dict[str, Any]:
    """
    Get the schema of a specific table from Qdrant database.

    Args:
        dataset_name: The name of the dataset to retrieve schema for.

    Returns:
        A dictionary with column details and schema information.
    """
    try:
        client = initialize_qdrant_client()

        search_result = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=Filter(
                should=[
                    FieldCondition(
                        key="metadata.name",
                        match=MatchValue(value=dataset_name),
                    ),
                    FieldCondition(
                        key="metadata.dataset_name",
                        match=MatchValue(value=dataset_name),
                    ),
                ]
            ),
            limit=1,
        )

        if not search_result[0]:
            return {
                "error": f"Dataset '{dataset_name}' not found in the database."
            }

        point = search_result[0][0]

        payload = point.payload or {}
        schema = payload.get("metadata", {}).get("schema", None)

        if not schema:
            return {
                "error": "Schema information not available for this dataset."
            }

        for column in schema.get("columns_details", []):
            if "stats" in column:
                del column["stats"]

        return schema

    except Exception as e:
        return {"error": f"Error retrieving schema from Qdrant: {e!s}"}


__tool__ = get_table_schema
