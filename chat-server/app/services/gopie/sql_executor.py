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

SQL_RESPONSE_TYPE = list[dict[str, Union[str, int, float, None]]]


@traceable(run_type="tool", name="execute_sql")
async def execute_sql(
    query: str,
) -> SQL_RESPONSE_TYPE:
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

    is_too_large = is_result_too_large(result)

    if is_too_large:
        truncated_result = truncate_result_for_llm(result)
        truncated_result.append(
            {
                "__note__": (
                    f"This result was large ({len(result)} rows) and has been "
                    f"truncated. User can see . "
                    f"Please let the user know that the result is truncated but "
                    f"the complete result is available with you."
                )
            }
        )
        return truncated_result

    return result
