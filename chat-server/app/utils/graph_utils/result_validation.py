import json
from typing import Any


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


def truncate_result_for_llm(result: Any) -> Any:
    """
    Truncate large results to make them suitable for LLM processing.

    Args:
        result: The query result to truncate

    Returns:
        Truncated result
    """
    if not isinstance(result, list):
        return result

    if len(result) <= 10:
        return result

    truncated = result[:10]

    if isinstance(truncated[0], dict):
        truncated.append(
            {
                "__note__": (
                    f"Result truncated for validation. "
                    f"Original had {len(result)} rows."
                )
            }
        )

    return truncated
