from typing import Any

from app.core.config import settings
from app.core.session import SingletonAiohttp
from app.services.gopie.sql_executor import execute_sql


async def generate_schema(dataset_name: str) -> tuple[Any, Any]:
    http_session = SingletonAiohttp.get_aiohttp_client()

    url = f"{settings.GOPIE_API_ENDPOINT}/v1/api/summary/{dataset_name}"
    headers = {"accept": "application/json"}

    sample_values_query = f"SELECT * FROM {dataset_name} LIMIT 5"
    sample_data = await execute_sql(sample_values_query)

    data = None

    async with http_session.get(url, headers=headers) as response:
        data = await response.json()

    return data, sample_data
