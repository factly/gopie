from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import ResultSummary
from app.utils.graph_utils.result_validation import is_result_too_large
from app.utils.graph_utils.summary_extraction import create_result_summary
from app.workflow.graph.multi_dataset_graph.types import State


async def validate_query_result(state: State) -> dict:
    """
    Validate if the current subquery result is small enough for LLM processing.
    If too large, mark the subquery's SQL queries as containing large results.

    Args:
        state: The current state object containing query results

    Returns:
        Updated state with large result flag for current subquery
    """
    query_result = state.get("query_result", None)
    messages = state.get("messages", [])
    subquery_index = state.get("subquery_index", 0)
    subquery = query_result.subqueries[subquery_index]

    # If previous step had an error, pass through without validation
    last_message = messages[-1] if messages else None
    if isinstance(last_message, ErrorMessage):
        pass

    result_messages = []
    summaries_created = False

    try:
        for i, sql_query_info in enumerate(subquery.sql_queries):
            if not sql_query_info.sql_query_result:
                continue

            is_too_large = is_result_too_large(
                result=sql_query_info.sql_query_result
            )

            if is_too_large:
                result = sql_query_info.sql_query_result
                if isinstance(result, list):
                    summary: ResultSummary = create_result_summary(
                        result=result
                    )
                    sql_query_info.sql_query_result = summary

                    result_messages.append(
                        f"Created summary for SQL query {i + 1} in subquery "
                        f"{subquery_index + 1} "
                        f"({len(result)} total rows)"
                    )
                    summaries_created = True

        if not summaries_created:
            message = "No large results found that needed summarization."
        else:
            message = "; ".join(result_messages)

        return {
            "query_result": query_result,
            "messages": [IntermediateStep(content=message)],
        }
    except Exception as e:
        error_msg = f"Query result validation error: {e!s}"
        if query_result:
            query_result.add_error_message(error_msg, "Result validation")

        return {
            "query_result": query_result,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
