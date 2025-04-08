import json
import logging

import requests
from app.core.config import settings
from app.core.langchain_config import lc
from app.models.message import ErrorMessage, IntermediateStep
from app.workflow.graph.types import State
from langchain_core.output_parsers import JsonOutputParser

SQL_API_ENDPOINT = f"{settings.GOPIE_API_ENDPOINT}/v1/api/sql"


async def execute_query(state: State) -> dict:
    """
    Execute the planned query using the external SQL API

    Args:
        state: The current state object containing messages and query information

    Returns:
        Updated state with query results or error messages
    """
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    try:
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        if not last_message or isinstance(last_message, ErrorMessage):
            raise ValueError("No valid query plan found in messages")

        content = (
            last_message.content
            if isinstance(last_message.content, str)
            else json.dumps(last_message.content)
        )

        parser = JsonOutputParser()
        query_plan = parser.parse(content)

        if not query_plan:
            raise ValueError("Failed to parse query plan from message")

        sql_query = query_plan.get("sql_query") or query_plan.get("sample_query")
        if not sql_query:
            raise ValueError("No SQL query found in plan")

        payload = {"query": sql_query}
        response = requests.post(SQL_API_ENDPOINT, json=payload)

        if response.status_code != 200:
            error_data = response.json()
            error_message = error_data.get("message", "Unknown error from SQL API")
            if response.status_code == 400:
                raise ValueError(f"Invalid SQL query: {error_message}")
            elif response.status_code == 403:
                raise ValueError(f"Non-SELECT statement: {error_message}")
            elif response.status_code == 404:
                raise ValueError(f"Table not found: {error_message}")
            else:
                raise ValueError(
                    f"SQL API error ({response.status_code}): {error_message}"
                )

        result_data = response.json()
        logging.info("sql query results: %s", result_data)

        if not result_data or (isinstance(result_data, list) and len(result_data) == 0):
            no_results_data = {
                "result": "Query executed successfully but returned no results",
                "query_executed": sql_query,
            }

            query_result.subqueries[query_index].query_result = []

            return {
                "query_result": query_result,
                "messages": [
                    IntermediateStep.from_text(json.dumps(no_results_data, indent=2))
                ],
            }

        result_records = result_data
        if not isinstance(result_data, list):
            if "data" in result_data:
                result_records = result_data["data"]
            else:
                result_records = [result_data]

        result_dict = {
            "result": "Query executed successfully",
            "query_executed": sql_query,
            "data": result_records,
        }

        query_result.subqueries[query_index].sql_query_used = sql_query
        query_result.subqueries[query_index].query_result = result_records

        return {
            "query_result": query_result,
            "messages": [IntermediateStep.from_text(json.dumps(result_dict, indent=2))],
        }

    except Exception as e:
        error_msg = f"Query execution error: {str(e)}"
        query_result.add_error_message(error_msg, "Query execution")

        return {
            "query_result": query_result,
            "messages": [
                ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))
            ],
            "retry_count": state.get("retry_count", 0) + 1,
        }


async def route_query_replan(state: State) -> str:
    """
    Determine whether to replan the query or generate results based on execution status

    Args:
        state: The current state containing messages and retry information

    Returns:
        Routing decision: "replan" or "generate_result"
    """
    last_message = state["messages"][-1]
    retry_count = state.get("retry_count", 0)

    if (
        isinstance(last_message, ErrorMessage)
        and retry_count < settings.MAX_RETRY_COUNT
    ):
        response = await lc.llm.ainvoke(
            f"""
                I got an error when executing the query: "{last_message.content}"

                Can you please tell whether this error can be solved by replanning the query? or it's need to reidentify the datasets?

                If it's need to reidentify the datasets, please return "reidentify_datasets"
                If it's need to replan the query, please return "replan"
                If it's no problem, please return "response_router"
            """
        )

        response_text = str(response.content).lower()

        if "reidentify_datasets" in response_text:
            return "reidentify_datasets"
        elif "replan" in response_text:
            return "replan"
        else:
            return "response_router"

    return "response_router"
