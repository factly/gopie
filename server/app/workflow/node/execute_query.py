from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.models.message import ErrorMessage, IntermediateStep
from app.services.gopie.sql_executor import execute_sql
from app.utils.model_registry.model_provider import get_llm_for_node
from app.workflow.graph.types import State


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
        sql_queries = query_result.subqueries[query_index].sql_queries
        if not sql_queries:
            raise ValueError("No SQL query/queries found in plan")

        for index, query_info in enumerate(sql_queries):
            result_records = await execute_sql(query_info.sql_query)

            if not result_records:
                raise ValueError("No results found for the query")

            result_dict = {
                "result": "Query executed successfully",
                "query_executed": query_info.sql_query,
                "data": result_records,
            }

            query_result.subqueries[query_index].sql_queries[
                index
            ].sql_query_result = result_records

        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": "SQL Execution completed",
            },
        )
        return {
            "query_result": query_result,
            "messages": [IntermediateStep.from_json(result_dict)],
        }

    except Exception as e:
        error_msg = f"Query execution error: {e!s}"
        query_result.add_error_message(error_msg, "Query execution")
        query_result.subqueries[query_index].retry_count += 1

        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": "Error in SQL Execution",
            },
        )
        return {
            "query_result": query_result,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }


async def route_query_replan(state: State, config: RunnableConfig) -> str:
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
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    subquery_errors = query_result.subqueries[query_index].error_message

    if (
        isinstance(last_message, ErrorMessage)
        and query_result.subqueries[query_index].retry_count
        < settings.MAX_RETRY_COUNT
    ):
        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": "do not stream",
            },
        )

        llm = get_llm_for_node("route_query_replan", config)

        response = await llm.ainvoke(
            {
                "input": f"""
                    I got an error when executing the query:
                    {last_message.content}

                    This are error message either from previous retrys or the
                    current try.
                    {subquery_errors}

                    Can you please tell whether this error can be solved by
                    replanning the query? or it's need to reidentify the
                    datasets?

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

        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": "continue streaming",
            },
        )

        response_text = str(response.content).lower()

        if "reidentify_datasets" in response_text:
            return "reidentify_datasets"
        elif "replan" in response_text:
            return "replan"
        else:
            return "validate_query_result"

    return "validate_query_result"
