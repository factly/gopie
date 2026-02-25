from app.core.config import settings
from app.core.log import custom_logger as logger
from app.models.schema import DatasetSummary
from app.services.gopie.client import GopieClient
from app.services.gopie.sql_executor import SQL_RESPONSE_TYPE, execute_sql
from app.utils.graph_utils.table_utils import (
    calculate_sampling_percentage,
    get_table_estimated_size,
    should_use_sampling,
)
from app.utils.olap import get_query_builder


def _build_sample_query(dataset_name: str, estimated_size: int, limit: int = 5) -> str:
    """Build optimized sample query based on table size.

    Uses the query builder to generate database-specific SQL syntax.

    Args:
        dataset_name: Name of the dataset/table
        estimated_size: Estimated row count from metadata
        limit: Number of distinct rows to return

    Returns:
        SQL query string
    """
    builder = get_query_builder()

    if not should_use_sampling(estimated_size):
        logger.debug(
            f"[{dataset_name}] Small dataset detected ({estimated_size} rows). "
            "Using standard nested query logic."
        )
        return builder.build_small_table_query(dataset_name, limit)
    else:
        pct_str = calculate_sampling_percentage(estimated_size)

        logger.debug(
            f"[{dataset_name}] Large dataset detected ({estimated_size} rows). "
            f"Sampling {pct_str}% to retrieve approx {settings.TARGET_ROWS} rows."
        )

        return builder.build_sample_query(dataset_name, pct_str, limit)


async def generate_summary(
    dataset_name: str,
    org_id: str,
    user_id: str,
    limit: int = 5,
) -> tuple[DatasetSummary, SQL_RESPONSE_TYPE]:
    """Generate dataset summary from Gopie API.

    Args:
        dataset_name: Name of the dataset
        org_id: Organization ID for multi-tenant support
        user_id: User ID for request authentication
        limit: Number of sample rows to fetch

    Returns:
        Tuple of DatasetSummary and sample data
    """
    client = GopieClient(org_id=org_id, user_id=user_id)
    path = f"/v1/api/summary/{dataset_name}?source=oltp"

    estimated_size = await get_table_estimated_size(dataset_name, org_id=org_id, user_id=user_id)
    sample_values_query = _build_sample_query(dataset_name, estimated_size, limit)
    sample_data = await execute_sql(query=sample_values_query, org_id=org_id, user_id=user_id)

    async with await client.get(path) as response:
        data = await response.json()

    if isinstance(data.get("summary"), dict) and "summary" in data["summary"]:
        data["summary"] = data["summary"]["summary"]

    return DatasetSummary(**data), sample_data
