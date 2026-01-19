import json

from langsmith import traceable

from app.core.config import settings
from app.core.log import custom_logger as logger


def is_result_too_large(result: list[dict]) -> tuple[bool, str]:
    """
    Determine if a SQL query result exceeds size limits for LLM processing.

    Returns:
        A tuple where the first element is True if the result is too large (based on record count,
        JSON size, or column count), and the second element is a string explaining the reason.
        If the result is acceptable or an error occurs, returns (False, "").
    """
    try:
        if len(result) > settings.ROW_TRUNCATION_LIMIT:
            return True, f"Query returned too many records: {len(result)}"

        result_json = json.dumps(result, default=str)
        if len(result_json) > settings.DATASET_TOKEN_TRUNCATION_LIMIT:
            return True, f"Query result is too large: {len(result_json)}"

        if (
            result
            and isinstance(result[0], dict)
            and len(result[0]) > settings.COLUMN_TRUNCATION_LIMIT
        ):
            return (
                True,
                f"Query returned too many columns: {len(result[0])}",
            )

        return False, ""
    except Exception as e:
        logger.exception(e)
        return False, ""


@traceable(run_type="tool", name="truncate_result_for_llm")
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
    if not result or len(result) <= settings.DISPLAY_ROWS_AFTER_TRUNCATION_LIMIT:
        return result

    truncated = result[: settings.DISPLAY_ROWS_AFTER_TRUNCATION_LIMIT]

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
