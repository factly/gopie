import json

from langchain_core.tools import tool
from qdrant_client.http.models import FieldCondition, Filter, MatchAny

from app.core.config import settings
from app.services.qdrant.qdrant_setup import initialize_qdrant_client


@tool
async def get_datasets_schemas(
    dataset_ids: list[str] = [],
    project_ids: list[str] = [],
) -> list[dict] | dict:
    """
    Get the schema of a specific tables from Qdrant database.

    Situation where it can be used:
        - User wants to know the schema of a specific dataset.
        - Want information related to datasets or get summary of datasets.

    Args:
        dataset_ids: The ids of the datasets to retrieve schema for.
        project_ids: The ids of the projects to retrieve schema for.

        Caution:
            - Requires atleast one of the dataset_ids or project_ids.

    Returns:
        A dictionary with schema information for the provided dataset ids.
    """
    try:
        client = initialize_qdrant_client()

        filter_conditions = []

        if dataset_ids:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.dataset_id",
                    match=MatchAny(any=dataset_ids),
                )
            )

        if project_ids:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.project_id",
                    match=MatchAny(any=project_ids),
                )
            )

        if filter_conditions:
            search_result = client.scroll(
                collection_name=settings.QDRANT_COLLECTION,
                scroll_filter=Filter(should=filter_conditions),
            )

        schemas = []
        for result in search_result:
            if result:
                payload = result[0].payload  # type: ignore
                if payload:
                    schema = json.loads(payload.get("page_content", "{}"))
                    schemas.append(schema)

        return schemas

    except Exception as e:
        return [
            {
                "error": f"Error retrieving schema from Qdrant: {e!s}",
                "dataset_ids": dataset_ids,
                "project_ids": project_ids,
            }
        ]


def get_dynamic_tool_text(args: dict) -> str:
    base_text = "Retrieving table schema information"
    dataset_name = args.get("dataset_name", "")
    if dataset_name:
        return f"{base_text} for '{dataset_name}'"
    return base_text


__tool__ = get_datasets_schemas
__tool_category__ = "Data Exploration"
__get_dynamic_tool_text__ = get_dynamic_tool_text
