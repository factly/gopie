import json

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.core.constants import SQL_QUERIES_GENERATED, SQL_QUERIES_GENERATED_ARG
from app.models.message import ErrorMessage
from app.services.gopie.sql_executor import execute_sql_with_full_and_truncated
from app.workflow.events.event_utils import non_streaming_dynamic_message
from app.workflow.graph.single_dataset_graph.types import State


async def execute_sql(state: State, config: RunnableConfig) -> dict:
    """
    Execute the final SQL queries (either approved by human or human-modified).

    Returns:
        dict: Updated state with SQL execution results
    """
    org_id = config.get("metadata", {}).get("org_id")
    user_id = config.get("metadata", {}).get("user")

    query_result = state.get("query_result", None)
    last_message = state.get("messages", [])

    if not query_result or not query_result.single_dataset_query_result:
        raise Exception("No query result available")

    non_sql_response = query_result.single_dataset_query_result.non_sql_response

    if non_sql_response or isinstance(last_message, ErrorMessage):
        return {
            "messages": [
                AIMessage(content="Either there is no SQL response or there is an error."),
            ],
            "query_result": query_result,
        }

    try:
        if not query_result.single_dataset_query_result.sql_queries:
            raise Exception("No SQL queries to execute")

        await non_streaming_dynamic_message(
            f"create a 1 to 2 sentence message saying that here are the generated SQL queries and "
            f"now let's execute them: {[result.sql_query for result in query_result.single_dataset_query_result.sql_queries]}",
            config,
        )

        for sql_info in query_result.single_dataset_query_result.sql_queries:
            try:
                org_id = config.get("metadata", {}).get("org_id") or ""
                user_id = config.get("metadata", {}).get("user") or ""
                result_data, truncated_result_data = await execute_sql_with_full_and_truncated(
                    query=sql_info.sql_query, org_id=org_id, user_id=user_id
                )
                sql_info.sql_query_result = truncated_result_data
                sql_info.full_sql_result = result_data
                sql_info.success = True
                sql_info.error = None

                await adispatch_custom_event(
                    "gopie-agent",
                    {
                        "content": "Executed SQL query",
                        "name": SQL_QUERIES_GENERATED,
                        "values": {SQL_QUERIES_GENERATED_ARG: [sql_info.sql_query]},
                    },
                )
            except Exception as err:
                error_str = str(err)
                sql_info.success = False
                sql_info.error = error_str

        return {
            "messages": [AIMessage(content=json.dumps(query_result.to_dict(), indent=2))],
            "query_result": query_result,
        }

    except Exception as e:
        error_message = f"Error executing SQL queries: {str(e)}"
        query_result.single_dataset_query_result.error = error_message

        return {
            "messages": [
                AIMessage(
                    content=(
                        f"I'm sorry, but I encountered an error while "
                        f"executing SQL queries: {error_message}"
                    )
                )
            ],
            "query_result": query_result,
        }
