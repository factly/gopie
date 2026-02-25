from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from qdrant_client import models

from app.core.config import settings
from app.core.log import custom_logger as logger
from app.services.qdrant.qdrant_setup import QdrantSetup


async def _fetch_datasets_from_qdrant(
    project_ids: list[str] | None = None,
    dataset_ids: list[str] | None = None,
) -> list[dict]:
    """
    Fetch dataset metadata from Qdrant by project_ids and/or dataset_ids.

    Returns:
        List of dicts with keys: name, dataset_name, project_id, dataset_id
    """
    should_conditions: list[models.Condition] = []

    if project_ids:
        should_conditions.append(
            models.FieldCondition(
                key="metadata.project_id",
                match=models.MatchAny(any=project_ids),
            )
        )

    if dataset_ids:
        should_conditions.append(
            models.FieldCondition(
                key="metadata.dataset_id",
                match=models.MatchAny(any=dataset_ids),
            )
        )

    if not should_conditions:
        return []

    query_filter = models.Filter(should=should_conditions)
    client = await QdrantSetup.get_async_client(settings.QDRANT_COLLECTION)

    results = []
    offset = None
    while True:
        response, next_offset = await client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=query_filter,
            limit=100,
            offset=offset,
            with_payload=[
                "metadata.name",
                "metadata.dataset_name",
                "metadata.project_id",
                "metadata.dataset_id",
            ],
        )
        for point in response:
            metadata = (point.payload or {}).get("metadata", {})
            results.append(
                {
                    "name": metadata.get("name", ""),
                    "dataset_name": metadata.get("dataset_name", ""),
                    "project_id": metadata.get("project_id", ""),
                    "dataset_id": metadata.get("dataset_id", ""),
                }
            )
        if next_offset is None:
            break
        offset = next_offset

    return results


def _format_datasets(datasets: list[dict]) -> str:
    project_map: dict[str, list[str]] = {}
    for ds in datasets:
        pid = ds["project_id"]
        label = ds["name"] or ds["dataset_name"] or ds["dataset_id"]
        project_map.setdefault(pid, []).append(label)

    lines = []
    for project_id, names in project_map.items():
        lines.append(f"Project {project_id}:")
        for name in names:
            lines.append(f"  - {name}")
    return "\n".join(lines)


@tool
async def get_all_datasets(
    project_ids: Annotated[list[str] | None, InjectedState("project_ids")],
    dataset_ids: Annotated[list[str] | None, InjectedState("dataset_ids")],
    config: RunnableConfig | None = None,
) -> str:
    """
    Get list of datasets names from project/dataset IDs in the current state.

    Note: At least one of the project_ids or dataset_ids must be present in state.

    Returns:
        List of dataset names
    """
    project_ids = project_ids or []
    dataset_ids = dataset_ids or []

    if not project_ids and not dataset_ids:
        logger.warning(
            "No project IDs or dataset IDs found in state. Cannot fetch datasets without specifying either."
        )
        return "No project IDs or dataset IDs found in state. Cannot fetch datasets without specifying either."

    try:
        datasets = await _fetch_datasets_from_qdrant(
            project_ids=project_ids or None,
            dataset_ids=dataset_ids or None,
        )
    except Exception as e:
        logger.exception(f"Error fetching datasets from Qdrant: {e}")
        return f"Error fetching datasets: {e}"

    if not datasets:
        return "No datasets found for the given project/dataset IDs."

    return _format_datasets(datasets)


def get_dynamic_tool_text(args: dict) -> str:
    return "Listing datasets..."


__tool__ = get_all_datasets
__get_dynamic_tool_text__ = get_dynamic_tool_text
__should_display_tool__ = True
__tool_category__ = "Data Discovery"
