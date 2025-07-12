from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.models.message import ErrorMessage, IntermediateStep
from app.services.gopie.sql_executor import execute_sql
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.graph.multi_dataset_graph.types import State


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
            result_records = await execute_sql(query=query_info.sql_query)

            if not result_records:
                raise ValueError("No results found for the query")

            query_result.subqueries[query_index].sql_queries[
                index
            ].sql_query_result = result_records

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "SQL Execution completed",
            },
        )
        return {
            "query_result": query_result,
            "messages": [IntermediateStep(content=str(result_records))],
        }

    except Exception as e:
        error_msg = f"Query execution error: {e!s}"
        query_result.add_error_message(error_msg, "Query execution")
        query_result.subqueries[query_index].retry_count += 1

        await adispatch_custom_event(
            "gopie-agent",
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
        Routing decision: "replan", "reidentify_datasets" or "route_response"
    """

    last_message = state["messages"][-1]
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    subquery_errors = query_result.subqueries[query_index].error_message
    node_messages = query_result.subqueries[query_index].node_messages

    if (
        isinstance(last_message, ErrorMessage)
        and query_result.subqueries[query_index].retry_count < settings.MAX_RETRY_COUNT
    ):
        prompt_messages = get_prompt(
            "route_query_replan",
            last_message_content=last_message.content,
            subquery_errors=subquery_errors,
            node_messages=node_messages,
        )

        llm = get_model_provider(config).get_llm_for_node("route_query_replan")

        response = await llm.ainvoke(prompt_messages)
        parsed_response = JsonOutputParser().parse(str(response.content))

        next_action = parsed_response.get("action", "route_response")

        if next_action == "reidentify_datasets" or next_action == "replan":
            return next_action

    return "route_response"
