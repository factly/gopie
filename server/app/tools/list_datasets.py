from typing import Dict, List

from app.core.config import settings
from app.core.session import SingletonAiohttp
from langchain_core.tools import tool

BASE_URL = settings.GOPIE_API_ENDPOINT


async def list_datasets(
    project_id: str,
    limit: int = 10,
    page: int = 1,
) -> List[Dict]:
    """
    List all datasets for a specific project.

    Args:
        project_id: The ID of the project to get datasets for
        limit: Maximum number of datasets to return per page
        page: The page number to fetch
        base_url: Base URL of the API

    Returns:
        List of datasets for the specified project
    """
    url = f"{BASE_URL}/v1/api/projects/{project_id}/datasets"
    params = {"limit": limit, "page": page}
    headers = {"accept": "application/json"}

    try:
        session = SingletonAiohttp.get_aiohttp_client()
        async with session.get(
            url, params=params, headers=headers, ssl=False
        ) as response:
            response.raise_for_status()
            return (await response.json()).get("results", [])
    except Exception as e:
        print(f"Error fetching datasets: {e}")
        return []


async def list_projects(limit: int = 10, page: int = 1) -> List[Dict]:
    """
    List all available projects.

    Args:
        limit: Maximum number of projects to return per page
        page: The page number to fetch
        base_url: Base URL of the API

    Returns:
        List of projects
    """
    url = f"{BASE_URL}/v1/api/projects"
    params = {"limit": limit, "page": page}
    headers = {"accept": "application/json"}

    try:
        session = SingletonAiohttp.get_aiohttp_client()
        async with session.get(
            url, params=params, headers=headers, ssl=False
        ) as response:
            response.raise_for_status()
            return (await response.json()).get("results", [])
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return []


@tool
async def get_all_datasets() -> List[Dict]:
    """
    Get all datasets from all projects.

    Args:
        base_url: Base URL of the API

    Returns:
        List of all datasets
    """
    all_datasets = []

    projects = await list_projects()

    for project in projects:
        project_id = project.get("id")
        if project_id:
            datasets = await list_datasets(project_id=project_id)
            for dataset in datasets:
                file_extension = ""
                if dataset.get("format", "") == "csv":
                    file_extension = ".csv"
                all_datasets.append(dataset.get("alias", "") + file_extension)

    return all_datasets


__tool__ = get_all_datasets
