from app.models.message import ErrorMessage, IntermediateStep
from app.utils.graph_utils.result_validation import is_result_too_large
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

    # If previous step had an error, pass through without validation
    last_message = messages[-1] if messages else None
    if isinstance(last_message, ErrorMessage):
        pass

    result_dict = {"message": "Validation completed successfully"}

    try:
        if query_result and hasattr(query_result, "subqueries"):
            if 0 <= subquery_index < len(query_result.subqueries):
                subquery = query_result.subqueries[subquery_index]

                large_result_found = False
                for i, sql_query_info in enumerate(subquery.sql_queries):
                    if not sql_query_info.sql_query_result:
                        continue

                    is_too_large, reason = is_result_too_large(
                        sql_query_info.sql_query_result
                    )

                    if is_too_large:
                        sql_query_info.contains_large_results = True
                        large_result_found = True

                        warning = (
                            f"SQL query {i + 1} in subquery "
                            f"{subquery_index + 1} "
                            f"result was too large: {reason}. "
                        )
                        warning += "Flagged for summary extraction."
                        query_result.add_error_message(
                            warning, "Result Size Warning"
                        )

                if large_result_found:
                    result_dict = {
                        "warning": "Query result was too large and has been "
                        "flagged for summary extraction",
                    }

        return {
            "query_result": query_result,
            "messages": [IntermediateStep.from_json(result_dict)],
        }

    except Exception as e:
        error_msg = f"Query result validation error: {e!s}"
        if query_result:
            query_result.add_error_message(error_msg, "Result validation")

        return {
            "query_result": query_result,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
