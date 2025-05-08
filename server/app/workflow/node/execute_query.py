from http import HTTPStatus
from typing import Any

import requests

from app.core.config import settings
from app.core.langchain_config import lc
from app.models.message import ErrorMessage, IntermediateStep
from app.workflow.graph.types import State

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
        response = requests.post(SQL_API_ENDPOINT, json=payload)
        if response.status_code != HTTPStatus.OK:
            error_data = response.json()
            error_message = error_data.get(
                "message", "Unknown error from SQL API"
            )
            if response.status_code == HTTPStatus.BAD_REQUEST:
                return {"error": f"Invalid SQL query: {error_message}"}
            elif response.status_code == HTTPStatus.FORBIDDEN:
                return {"error": f"Non-SELECT statement: {error_message}"}
            elif response.status_code == HTTPStatus.NOT_FOUND:
                return {"error": f"Table not found: {error_message}"}
            else:
                error = (
                    f"SQL API error ({response.status_code}): {error_message}"
                )
                return {"error": error}

        result_data = response.json()

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


async def execute_query(state: State) -> dict:
    """
    Execute the planned query using the external SQL API

    Args:
        state: The current state object containing messages and
               query information

    Returns:
        Updated state with query results or error messages
    """
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    try:
        last_message = (
            state.get("messages", [])[-1] if state.get("messages") else None
        )
        if not last_message or isinstance(last_message, ErrorMessage):
            raise ValueError("No valid query plan found in messages")

        query_plan = last_message.content[0]

        if not query_plan:
            raise ValueError("Failed to parse query plan from message")

        sql_query = query_plan.get("sql_query")
        if not sql_query:
            raise ValueError("No SQL query found in plan")

        result = await execute_sql(sql_query)

        if isinstance(result, dict) and "error" in result:
            raise ValueError(result["error"])

        result_records = result

        result_dict = {
            "result": "Query executed successfully",
            "query_executed": sql_query,
            "data": result_records,
        }

        query_result.subqueries[query_index].sql_query_used = sql_query
        query_result.subqueries[query_index].query_result = result_records

        return {
            "query_result": query_result,
            "messages": [IntermediateStep.from_json(result_dict)],
        }

    except Exception as e:
        error_msg = f"Query execution error: {e!s}"
        query_result.add_error_message(error_msg, "Query execution")

        return {
            "query_result": query_result,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
            "retry_count": state.get("retry_count", 0) + 1,
        }


async def route_query_replan(state: State) -> str:
    """
    Determine whether to replan the query or generate results based on
    execution status

    Args:
        state: The current state containing messages and retry information

    Returns:
        Routing decision: "replan", "reidentify_datasets", or
        "validate_query_result"
    """
    last_message = state["messages"][-1]
    retry_count = state.get("retry_count", 0)

    if (
        isinstance(last_message, ErrorMessage)
        and retry_count < settings.MAX_RETRY_COUNT
    ):
        response = await lc.llm.ainvoke(
            {
                "input": f"""
                I got an error when executing the query:
                "{last_message.content}"

                Can you please tell whether this error can be solved by
                replanning the query? or it's need to reidentify the datasets?

                If it's need to reidentify the datasets, please return
                "reidentify_datasets"
                If it's need to replan the query, please return "replan"
                If it's no problem, please return "validate_query_result"

                Think through this step-by-step:
                1. Analyze the error message
                2. Determine if it's a schema/dataset issue
                3. Check if it's a query syntax issue
                4. Decide on the appropriate action
            """
            }
        )

        response_text = str(response.content).lower()

        if "reidentify_datasets" in response_text:
            return "reidentify_datasets"
        elif "replan" in response_text:
            return "replan"
        else:
            return "validate_query_result"

    return "validate_query_result"
