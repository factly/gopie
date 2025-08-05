from http import HTTPStatus
from typing import Union

from langsmith import traceable

from app.core.config import settings
from app.core.log import logger
from app.core.session import SingletonAiohttp
from app.utils.graph_utils.result_validation import (
    is_result_too_large,
    truncate_result_for_llm,
)

SQL_API_ENDPOINT = f"{settings.GOPIE_API_ENDPOINT}/v1/api/sql"

SQL_RESPONSE_TYPE = list[dict[str, Union[str, int, float, None]]] | None


@traceable(run_type="tool", name="execute_sql")
async def execute_sql(query: str) -> SQL_RESPONSE_TYPE:
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
            logger.error(error_data.get("error", "Unknown error"))
            raise Exception(error_data.get("error", "Unknown error"))

        result_data = await response.json()

    result = result_data["data"]
    return result


async def execute_sql_with_limit(query: str) -> SQL_RESPONSE_TYPE:
    """
    Execute a SQL query with a limit against the SQL API
    """
    result = await execute_sql(query=query)
    return truncate_if_too_large(result)


def truncate_if_too_large(result: SQL_RESPONSE_TYPE) -> SQL_RESPONSE_TYPE:
    if result is None:
        return result

    is_too_large, reason = is_result_too_large(result)
    if is_too_large:
        logger.info(f"Result is too large, reason: {reason}")
        truncated_result = truncate_result_for_llm(result)
        return truncated_result
    return result
