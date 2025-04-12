from typing import Any

from app.core.config import settings
from app.core.session import SingletonAiohttp
from app.models.data import Dataset_details
from app.models.schema import DatasetSchema


async def get_dataset_info(dataset_id, project_id) -> Dataset_details:
    http_session = SingletonAiohttp.get_aiohttp_client()

    url = f"{settings.GOPIE_API_ENDPOINT}/v1/api/projects/{project_id}/datasets/{dataset_id}"
    headers = {"accept": "application/json"}

    async with http_session.get(url, headers=headers) as response:
        data = await response.json()
        return Dataset_details(**data)


def format_schema(
    schema: Any,
    project_id: str,
    dataset_id: str,
    file_path: str,
):
    columns_details = []
    if schema.get("samples") and len(schema["samples"]) > 0:
        sample_data = schema["samples"][0].get("data", {})
        variables = schema.get("variables", {})

        for column_name, column_values in sample_data.items():
            sample_values = list(column_values.values())[:5]
            non_null_count = sum(1 for v in column_values.values() if v is not None)
            columns_details.append(
                {
                    "name": column_name,
                    "description": f"Column containing {column_name} data",
                    "type": variables.get(column_name, {}).get("type", "string"),
                    "sample_values": sample_values,
                    "non_null_count": non_null_count,
                    "stats": variables.get(column_name, {}),
                }
            )

    formatted_schema: DatasetSchema = {
        "name": "will add it later",
        "dataset_name": "will add it later",
        "dataset_description": "will add it later",
        "project_id": project_id,
        "dataset_id": dataset_id,
        "file_path": file_path,
        "analysis": schema["analysis"],
        "row_count": schema["table"]["n"],
        "col_count": schema["table"]["n_var"],
        "columns": schema["columns"],
        "columns_details": columns_details,
        "alerts": schema["alerts"],
        "duplicates": schema["duplicates"],
        "correlations": schema["correlations"],
        "missing_values": schema["missing"],
    }

    # column_descriptions = generate_column_descriptions(formatted_schema)

    # for column in formatted_schema["columns_details"]:
    #     if column["name"] in column_descriptions:
    #         column["description"] = column_descriptions[column["name"]]

    return formatted_schema
