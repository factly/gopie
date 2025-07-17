from langchain_core.callbacks.manager import adispatch_custom_event

from app.models.message import ErrorMessage, IntermediateStep
from app.services.gopie.sql_executor import execute_sql
from app.workflow.graph.multi_dataset_graph.types import State
from app.models.query import SqlQueryInfo


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

        sql_results: list[SqlQueryInfo] = []

        for query_info in sql_queries:
            try:
                result_data = await execute_sql(query=query_info.sql_query)
                sql_results.append(
                    SqlQueryInfo(
                        sql_query=query_info.sql_query,
                        explanation=query_info.explanation,
                        sql_query_result=result_data,
                        success=True,
                        error=None,
                    )
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
