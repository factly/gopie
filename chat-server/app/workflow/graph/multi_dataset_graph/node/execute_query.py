from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.models.message import ErrorMessage, IntermediateStep
from app.services.gopie.sql_executor import execute_sql
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
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
            "gopie-agent",
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
        Routing decision: "replan", "reidentify_datasets", or
        "validate_query_result"
    """

    last_message = state["messages"][-1]
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    subquery_errors = query_result.subqueries[query_index].error_message
    node_messages = query_result.subqueries[query_index].node_messages

    if (
        isinstance(last_message, ErrorMessage)
        and query_result.subqueries[query_index].retry_count
        < settings.MAX_RETRY_COUNT
    ):
        llm = get_llm_for_node("route_query_replan", config)

        prompt = f"""
I encountered an error when executing the SQL query:
{last_message.content}

Previous error messages (including current attempt):
{subquery_errors}

Node execution messages and context:
{node_messages}

ANALYSIS INSTRUCTIONS:
Analyze all available information carefully to determine the best next action.
Consider the nature of the error, the execution context in node_messages,
and what previous attempts have revealed.

AVAILABLE OPTIONS:

1. "reidentify_datasets"
   Choose this when the underlying dataset structure doesn't match what was
   expected

2. "replan"
   Choose this when the query itself needs reformulation but the dataset
   understanding is correct

3. "validate_query_result"
   Choose this when either:
   - The current results are sufficient despite the error
   - Further retries would be futile
   - The error is expected and doesn't prevent moving forward
   - Analyzing the data and found that the error is not fixable by retrying
     the query

IMPORTANT NOTES:
- "validate_query_result" doesn't mean success - it means we proceed with
  what we have
- Avoid making simplistic decisions based solely on error keywords
- Synthesize all available context to determine the most appropriate action

RESPONSE FORMAT:
Return ONLY one of these exact strings: "reidentify_datasets", "replan", or
"validate_query_result"
        """

        response = await llm.ainvoke(
            {
                "chat_history": get_chat_history(config),
                "input": HumanMessage(content=prompt),
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
