import json

from langchain_core.tools import tool
from qdrant_client.http.models import FieldCondition, Filter, MatchAny

from app.core.config import settings
from app.core.log import logger
from app.models.schema import DatasetSchema
from app.services.qdrant.qdrant_setup import QdrantSetup


@tool
async def get_datasets_schemas(
    dataset_ids: list[str] = [],
    project_ids: list[str] = [],
    status_message: str = "",
) -> str:
    """
    Get the schema of a specific tables from Qdrant database.

    ONLY use this tool when:
        - If user wants want information about the dataset.
        - If user wants to summarize the dataset.
        - If user wants to know the structure/schema of this dataset.

    DO NOT use this tool when:
        - If you want information about the dataset.
          Because further steps already have full workflow to get the
          information and then process it.


    Args:
        dataset_ids: The ids of the datasets to retrieve schema for.
        project_ids: The ids of the projects to retrieve schema for.
        status_message: Short, friendly message to show the user about this action
            (<= 120 chars). Mention if this is a retry and why you're retrying, when applicable.

        Caution:
            - Requires atleast one of the dataset_ids or project_ids.

    Returns:
        A dictionary with schema information for the provided dataset ids.
    """
    try:
        client = await QdrantSetup.get_async_client()

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
            search_result = await client.scroll(
                collection_name=settings.QDRANT_COLLECTION,
                scroll_filter=Filter(should=filter_conditions),
            )

        schemas = []
        if search_result[0]:
            for point in search_result[0]:
                payload = point.payload
                if payload:
                    try:
                        metadata = payload.get("metadata", {})
                        dataset_schema = DatasetSchema(**metadata)
                        schemas.append(dataset_schema.format_for_prompt())
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing schema JSON: {e}")
                        continue

        return "\n\n".join(schemas)

    except Exception as e:
        return f"Error retrieving schema from Qdrant: {e!s}"


def get_dynamic_tool_text(args: dict) -> str:
    return args.get("status_message") or "Retrieving dataset schemas"


__tool__ = get_datasets_schemas
__tool_category__ = "Data Exploration"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
