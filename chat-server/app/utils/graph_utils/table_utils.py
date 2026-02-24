from app.core.config import settings
from app.core.log import custom_logger as logger
from app.services.gopie.sql_executor import execute_sql
from app.utils.olap import get_query_builder


async def get_table_estimated_size(table_name: str, org_id: str, user_id: str) -> int:
    """Get estimated table size from OLAP backend metadata.

    Args:
        table_name: Name of the table
        org_id: Organization ID for multi-tenant support
        user_id: User ID for request authentication

    Returns:
        Estimated row count, or 0 if table not found or error occurs
    """
    builder = get_query_builder()
    size_query = builder.get_estimated_size_query(table_name)
    try:
        result = await execute_sql(query=size_query, org_id=org_id, user_id=user_id)
        if result and len(result) > 0:
            estimated_size = result[0].get("estimated_size", 0)
            return int(estimated_size) if estimated_size else 0
    except Exception as e:
        logger.warning(
            f"Failed to get estimated_size for {table_name}: {e}. "
            "Defaulting to small table strategy."
        )
    return 0


def calculate_sampling_percentage(estimated_size: int) -> str:
    """Calculate sampling percentage to target TARGET_ROWS.

    Args:
        estimated_size: Estimated row count from metadata

    Returns:
        Formatted percentage string with 6 decimal precision
    """
    sample_pct = (settings.TARGET_ROWS / estimated_size) * 100
    return f"{sample_pct:.6f}"


def should_use_sampling(estimated_size: int) -> bool:
    """Determine if sampling strategy should be used based on table size.

    Args:
        estimated_size: Estimated row count from metadata

    Returns:
        True if table size exceeds threshold, False otherwise
    """
    return estimated_size > settings.SAMPLING_THRESHOLD
