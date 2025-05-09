from http import HTTPStatus
from typing import Any

from app.core.config import settings
from app.core.session import SingletonAiohttp

SQL_API_ENDPOINT = f"{settings.GOPIE_API_ENDPOINT}/v1/api/sql"


async def execute_sql(
    query: str,
) -> dict[str, Any] | list[dict[str, Any]]:
    """
    Execute a SQL query against the SQL API

    Args:
        query: The SQL query to execute

    Returns:
        Query results or error information
    """
    try:
        payload = {"query": query}

        http_session = SingletonAiohttp.get_aiohttp_client()

        async with http_session.post(
            SQL_API_ENDPOINT, json=payload
        ) as response:
            if response.status != HTTPStatus.OK:
                error_data = await response.json()
                error_message = error_data.get(
                    "message", "Unknown error from SQL API"
                )

                if response.status == HTTPStatus.BAD_REQUEST:
                    return {"error": f"Invalid SQL query: {error_message}"}
                elif response.status == HTTPStatus.FORBIDDEN:
                    return {"error": f"Non-SELECT statement: {error_message}"}
                elif response.status == HTTPStatus.NOT_FOUND:
                    return {"error": f"Table not found: {error_message}"}
                else:
                    error = (
                        f"SQL API error ({response.status}): {error_message}"
                    )
                    return {"error": error}

        result_data = await response.json()

        if not result_data or (
            isinstance(result_data, list) and len(result_data) == 0
        ):
            return {"result": "No results found for the query"}

        result_records = result_data
        if not isinstance(result_data, list):
            if "data" in result_data:
                result_records = result_data["data"]
            else:
                result_records = [result_data]

        return result_records
    except Exception as e:
        return {"error": f"Query execution error: {e!s}"}
