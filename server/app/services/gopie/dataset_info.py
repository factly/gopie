from typing import Any

from app.core.config import settings
from app.core.session import SingletonAiohttp
from app.models.data import DatasetDetails
from app.models.schema import ColumnSchema, DatasetSchema


async def get_dataset_info(dataset_id, project_id) -> DatasetDetails:
    http_session = SingletonAiohttp.get_aiohttp_client()

    url = (
        f"{settings.GOPIE_API_ENDPOINT}/v1/api/projects/{project_id}/"
        f"datasets/{dataset_id}"
    )
    headers = {"accept": "application/json"}

    async with http_session.get(url, headers=headers) as response:
        data = await response.json()
        return DatasetDetails(**data)


def format_schema(
    schema: Any,
    sample_data: Any,
    project_id: str,
    dataset_id: str,
):
    """
    Format the schema data into a standardized structure.

    Args:
        schema: The schema data containing the 'summary' field with column info
        sample_data: Sample data for the dataset
        project_id: The project ID
        dataset_id: The dataset ID

    Returns:
        A formatted DatasetSchema object
    """
    columns: list[ColumnSchema] = []

    schema_data = schema["summary"]
    columns_data = schema_data.get("summary", [])

    for column_data in columns_data:
        column_name = column_data.get("column_name")

        samples = (
            sample_data[column_name].tolist()
            if column_name in sample_data
            else []
        )

        column_schema: ColumnSchema = {
            "column_name": column_name,
            "column_type": column_data.get("column_type", ""),
            "min": column_data.get("min"),
            "max": column_data.get("max"),
            "approx_unique": column_data.get("approx_unique"),
            "avg": column_data.get("avg"),
            "std": column_data.get("std"),
            "q25": column_data.get("q25"),
            "q50": column_data.get("q50"),
            "q75": column_data.get("q75"),
            "count": column_data.get("count"),
            "sample_values": samples,
            "null_percentage": column_data.get("null_percentage", {}),
        }

        columns.append(column_schema)

    formatted_schema: DatasetSchema = {
        "name": "will add it later",
        "dataset_name": "will add it later",
        "dataset_description": "will add it later",
        "project_id": project_id,
        "dataset_id": dataset_id,
        "columns": columns,
    }

    return formatted_schema
