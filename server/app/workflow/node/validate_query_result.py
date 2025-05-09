import json
from typing import Any

from app.models.message import ErrorMessage, IntermediateStep
from app.workflow.graph.types import State


def is_result_too_large(result: Any) -> tuple[bool, str]:
    """
    Check if the result from SQL query is too large for LLM processing.

    Args:
        result: The query result to check

    Returns:
        Tuple of (is_too_large, reason)
    """
    try:
        if isinstance(result, list):
            if len(result) > 200:
                return True, f"Query returned too many records: {len(result)}"

            result_json = json.dumps(result)
            # ~25k tokens approximation
            if len(result_json) > 100000:
                return True, f"Query result is too large: {len(result_json)}"

            # Check number of columns in first record
            if result and isinstance(result[0], dict) and len(result[0]) > 50:
                return (
                    True,
                    f"Query returned too many columns: {len(result[0])}",
                )

        # For non-list results, check the total size
        elif isinstance(result, dict):
            result_json = json.dumps(result)
            if len(result_json) > 100000:
                return (
                    True,
                    f"Query result is too large: {len(result_json)}",
                )

        return False, ""
    except Exception:
        return False, ""


async def validate_query_result(state: State) -> dict:
    """
    Validate if the current subquery result is small enough for LLM processing.
    If too large, mark the subquery as containing large results.

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

                if not subquery.query_result:
                    pass

                is_too_large, reason = is_result_too_large(
                    subquery.query_result
                )

                if is_too_large:
                    subquery.contains_large_results = True

                    warning = (
                        f"Subquery {subquery_index+1} result was too large: "
                        f"{reason}. "
                    )
                    warning += "Flagged for summary extraction."
                    query_result.add_error_message(
                        warning, "Result Size Warning"
                    )

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
