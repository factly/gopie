from langchain_core.tools import tool

from app.core.config import settings
from app.core.log import logger
from app.core.session import SingletonAiohttp

BASE_URL = settings.GOPIE_API_ENDPOINT


async def get_dataset_names_from_project_ids(project_ids: list[str]) -> str:
    project_dataset_map = {}
    session = SingletonAiohttp.get_aiohttp_client()

    for project_id in project_ids:
        try:
            url = f"{BASE_URL}/v1/api/projects/{project_id}/datasets"
            headers = {"accept": "application/json"}

            async with session.get(url, headers=headers, ssl=False) as response:
                if response.status == 200:
                    dataset_data = await response.json()
                    project_dataset_map[project_id] = dataset_data
                else:
                    logger.warning(f"Failed to fetch datasets from project {project_id}")
        except Exception as e:
            logger.exception(f"Error fetching datasets from project {project_id}: {e}")

    list_of_datasets_str = ""
    for project_id, datasets in project_dataset_map.items():
        list_of_datasets_str += f"Project {project_id}:\n"
        for dataset in datasets:
            list_of_datasets_str += f"  - {dataset.get('alias', '')}\n"
    return list_of_datasets_str


async def get_project_ids_for_datasets_ids(dataset_ids: list[str]) -> dict[str, str]:
    dataset_id_project_map = {}
    session = SingletonAiohttp.get_aiohttp_client()
    for dataset_id in dataset_ids:
        url = f"{BASE_URL}/v1/api/datasets/{dataset_id}/project"
        headers = {"accept": "application/json"}
        async with session.get(url, headers=headers, ssl=False) as response:
            if response.status == 200:
                dataset_data = await response.json()
                dataset_id_project_map[dataset_id] = dataset_data.get("project_id", "")
            else:
                logger.warning(f"Dataset {dataset_id} not found")
    return dataset_id_project_map


async def get_dataset_names_for_dataset_ids(dataset_project_ids_map: dict[str, str]) -> str:
    project_dataset_map = {}
    session = SingletonAiohttp.get_aiohttp_client()

    for dataset_id, project_id in dataset_project_ids_map.items():
        url = f"{BASE_URL}/v1/api/projects/{project_id}/datasets/{dataset_id}"
        headers = {"accept": "application/json"}

        async with session.get(url, headers=headers, ssl=False) as response:
            if response.status == 200:
                dataset_data = await response.json()
                project_dataset_map[project_id] = dataset_data.get("alias", "")
            else:
                logger.warning(f"Dataset {dataset_id} not found")

    list_of_datasets_str = ""
    for project_id, dataset_name in project_dataset_map.items():
        list_of_datasets_str += f"Project {project_id}:\n"
        list_of_datasets_str += f"  - {dataset_name}\n"
    return list_of_datasets_str


@tool
async def get_all_datasets(
    status_message: str = "",
    project_ids: list[str] = [],
    dataset_ids: list[str] = [],
) -> str:
    """
    Get list of datasets names from provided project ids and dataset ids.

    status_message: Short, friendly message to show the user about this action
            (<= 120 chars). Mention if this is a retry and why you're retrying, when applicable.

    Args:
        project_ids: Optional list of project IDs to fetch all datasets from these projects.
        dataset_ids: Optional list of specific dataset IDs to fetch.

    Note: Atleast one of the project_ids or dataset_ids must be provided.

    Returns:
        List of dataset names
    """
    if not project_ids and not dataset_ids:
        logger.warning(
            "No project IDs or dataset IDs provided. Cannot fetch datasets without specifying either."
        )
        return "No project IDs or dataset IDs provided. Cannot fetch datasets without specifying either."

    all_datasets: list[str] = [""]

    if project_ids:
        dataset_names = await get_dataset_names_from_project_ids(project_ids)
        all_datasets.append(dataset_names)

    if dataset_ids:
        dataset_project_ids_map = await get_project_ids_for_datasets_ids(dataset_ids=dataset_ids)
        all_datasets.append(await get_dataset_names_for_dataset_ids(dataset_project_ids_map))

    return "\n".join(all_datasets)


def get_dynamic_tool_text(args: dict) -> str:
    return args.get("status_message") or "Listing specific datasets by ID"


__tool__ = get_all_datasets
__get_dynamic_tool_text__ = get_dynamic_tool_text
__should_display_tool__ = True
__tool_category__ = "Data Discovery"
