from http import HTTPStatus
from typing import Union

from langsmith import traceable

from app.core.log import custom_logger as logger
from app.services.gopie.client import GopieClient
from app.utils.graph_utils.result_validation import (
    is_result_too_large,
    truncate_result_for_llm,
)

SQL_RESPONSE_TYPE = list[dict[str, Union[str, int, float, None]]] | None


@traceable(name="execute_sql", run_type="tool")
async def execute_sql(query: str, org_id: str, user_id: str) -> SQL_RESPONSE_TYPE:
    """
    Execute a SQL query against the SQL API

    Args:
        query: The SQL query to execute
        org_id: Organization ID for multi-tenant support
        user_id: User ID for request authentication

    Returns:
        Query results or error information
    """
    payload = {"query": query}
    client = GopieClient(org_id=org_id, user_id=user_id)
    path = "/v1/api/sql"

    async with await client.post(path, json=payload) as response:
        if response.status != HTTPStatus.OK:
            error_data = await response.json()
            raise Exception(error_data.get("error", "Unknown error"))

        result_data = await response.json()

    result = result_data["data"]
    return result


async def execute_sql_with_limit(query: str, org_id: str, user_id: str) -> SQL_RESPONSE_TYPE:
    result = await execute_sql(query=query, org_id=org_id, user_id=user_id)
    return truncate_if_too_large(result)


async def execute_sql_with_full_and_truncated(
    query: str,
    org_id: str,
    user_id: str,
) -> tuple[SQL_RESPONSE_TYPE, SQL_RESPONSE_TYPE]:
    full_result = await execute_sql(query=query, org_id=org_id, user_id=user_id)
    truncated_result = truncate_if_too_large(full_result)
    return full_result, truncated_result


def truncate_if_too_large(result: SQL_RESPONSE_TYPE) -> SQL_RESPONSE_TYPE:
    if result is None:
        return result

    is_too_large, reason = is_result_too_large(result=result)
    if is_too_large:
        logger.info(f"Result is too large, reason: {reason}")
        truncated_result = truncate_result_for_llm(result=result)
        return truncated_result
    return result
