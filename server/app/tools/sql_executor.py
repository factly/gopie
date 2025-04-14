from typing import Any, Dict

import requests
from app.core.config import settings

SQL_API_ENDPOINT = f"{settings.GOPIE_API_ENDPOINT}/v1/api/sql"


def execute_sql_query(query: str) -> Dict[str, Any]:
    """
    Execute SQL query using the external SQL API

    Args:
        query: The SQL query to execute

    Returns:
        Dictionary containing query results or error information
    """
    try:
        response = requests.post(SQL_API_ENDPOINT, json={"query": query})

        if response.status_code != 200:
            error_data = response.json()
            error_message = error_data.get("message", "Unknown error from SQL API")

            return {
                "error": f"SQL API error ({response.status_code}): {error_message}",
                "query_executed": query,
            }

        result_data = response.json()

        if not result_data or (isinstance(result_data, list) and len(result_data) == 0):
            return {
                "result": "Query executed successfully but returned no results",
                "query_executed": query,
                "data": [],
            }

        result_records = result_data
        if not isinstance(result_data, list):
            if "data" in result_data:
                result_records = result_data["data"]
            else:
                result_records = [result_data]

        return {
            "result": "Query executed successfully",
            "query_executed": query,
            "data": result_records,
        }

    except Exception as e:
        return {"error": f"Query execution error: {str(e)}", "query_executed": query}
