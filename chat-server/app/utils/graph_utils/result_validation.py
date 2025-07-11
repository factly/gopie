import json


def is_result_too_large(result: list[dict]) -> tuple[bool, str]:
    """
    Check if the result from SQL query is too large for LLM processing.

    Args:
        result: The query result to check

    Returns:
        Tuple of (is_too_large, reason)
    """
    try:
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

        return False, ""
    except Exception:
        return False, ""


def truncate_result_for_llm(result: list[dict] | None) -> list[dict] | None:
    """
    Truncate large results to make them suitable for LLM processing.

    Args:
        result: The query result to truncate

    Returns:
        Truncated result
    """
    if not result or len(result) <= 10:
        return result

    truncated = result[:10]

    if isinstance(truncated[0], dict):
        truncated.append(
            {
                "__note__": (
                    f"This result was large ({len(result)} rows) and has been "
                    f"truncated. User can see . "
                    f"Please let the user know that the result is truncated but "
                    f"the complete result is available with you."
                )
            }
        )

    return truncated
