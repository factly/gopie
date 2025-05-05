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
    file_path: str,
):
    columns: list[ColumnSchema] = []

    for _, row in schema.iterrows():
        column_name = row.get("column_name")
        column_type = row.get("column_type")

        samples = (
            sample_data[column_name].tolist()
            if column_name in sample_data
            else []
        )

        column_schema: ColumnSchema = {
            "column_name": column_name,
            "column_type": column_type,
            "min": row.get("min"),
            "max": row.get("max"),
            "approx_unique": row.get("approx_unique"),
            "avg": row.get("avg"),
            "std": row.get("std"),
            "q25": row.get("q25"),
            "q50": row.get("q50"),
            "q75": row.get("q75"),
            "count": row.get("count"),
            "sample_values": samples,
            "null_percentage": row.get("null_percentage", 0.0),
        }

        columns.append(column_schema)

    formatted_schema: DatasetSchema = {
        "name": "will add it later",
        "dataset_name": "will add it later",
        "dataset_description": "will add it later",
        "project_id": project_id,
        "dataset_id": dataset_id,
        "file_path": file_path,
        "columns": columns,
    }

    return formatted_schema
