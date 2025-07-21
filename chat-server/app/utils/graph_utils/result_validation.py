import json

from app.core.log import logger


def is_result_too_large(result: list[dict]) -> tuple[bool, str]:
    """
    Determine if a SQL query result exceeds size limits for LLM processing.

    Returns:
        A tuple where the first element is True if the result is too large (based on record count, JSON size, or column count),
        and the second element is a string explaining the reason. If the result is acceptable or an error occurs, returns (False, "").
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
    except Exception as e:
        logger.exception(e, exc_info=True, stack_info=True)
        return False, ""


def truncate_result_for_llm(result: list[dict] | None) -> list[dict] | None:
    """
    Truncates a SQL query result to a maximum of 10 records for LLM processing.

    If the input is `None` or contains 10 or fewer records, it is returned unchanged.
    For larger results, only the first 10 records are kept,
    and a note is appended indicating the truncation and availability of the full result.

    Returns:
        The truncated result list with an appended note if truncation occurred,
        or the original result if no truncation was needed.
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
