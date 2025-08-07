from langchain_core.callbacks.manager import adispatch_custom_event

from app.core.constants import SQL_QUERIES_GENERATED, SQL_QUERIES_GENERATED_ARG
from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import SqlQueryInfo
from app.services.gopie.sql_executor import execute_sql, truncate_if_too_large
from app.workflow.graph.multi_dataset_graph.types import State


async def execute_query(state: State) -> dict:
    """
    Executes all planned SQL queries for the current subquery in the workflow state and updates the state with results or error messages.

    Each SQL query is executed asynchronously, and the outcome (success or failure) is recorded in the state.
    On completion, the function dispatches a custom event and returns the updated state along with a message summarizing the results.
    If an error occurs during execution, the error is recorded, the retry count is incremented, and an error message is returned.
    If no SQL queries are present (no-SQL response case), the function skips execution and returns the state unchanged.
    """
    last_message = state.get("messages", [])[-1]
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    if isinstance(last_message, ErrorMessage):
        pass

    try:
        sql_queries = query_result.subqueries[query_index].sql_queries

        if not sql_queries:
            pass

        sql_results: list[SqlQueryInfo] = []

        for query_info in sql_queries:
            try:
                full_result_data = await execute_sql(query=query_info.sql_query)
                result_data = truncate_if_too_large(full_result_data)
                sql_results.append(
                    SqlQueryInfo(
                        sql_query=query_info.sql_query,
                        explanation=query_info.explanation,
                        sql_query_result=result_data,
                        full_sql_result=full_result_data,
                        success=True,
                        error=None,
                    )
                )
                await adispatch_custom_event(
                    "gopie-agent",
                    {
                        "content": "Executed SQL query",
                        "name": SQL_QUERIES_GENERATED,
                        "values": {SQL_QUERIES_GENERATED_ARG: [query_info.sql_query]},
                    },
                )
            except Exception as err:
                error_str = str(err)
                sql_results.append(
                    SqlQueryInfo(
                        sql_query=query_info.sql_query,
                        explanation=query_info.explanation,
                        sql_query_result=None,
                        success=False,
                        error=error_str,
                    )
                )

        query_result.subqueries[query_index].sql_queries = sql_results

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "SQL Execution completed",
            },
        )
        return {
            "query_result": query_result,
            "messages": [IntermediateStep(content=str(sql_results))],
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
