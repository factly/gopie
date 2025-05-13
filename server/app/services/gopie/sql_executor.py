import logging
from http import HTTPStatus

from app.core.config import settings
from app.core.session import SingletonAiohttp

SQL_API_ENDPOINT = f"{settings.GOPIE_API_ENDPOINT}/v1/api/sql"


async def execute_sql(
    query: str,
) -> list:
    """
    Execute a SQL query against the SQL API

    Args:
        query: The SQL query to execute

    Returns:
        Query results or error information
    """
    payload = {"query": query}

    http_session = SingletonAiohttp.get_aiohttp_client()

    async with http_session.post(SQL_API_ENDPOINT, json=payload) as response:
        if response.status != HTTPStatus.OK:
            error_data = await response.json()
            logging.error(error_data.get("error", "Unknown error"))
            raise Exception(error_data.get("message", "Unknown error"))

        result_data = await response.json()

    return result_data["data"]
