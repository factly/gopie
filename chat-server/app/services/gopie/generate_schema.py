from typing import Optional

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


def _build_sample_query(dataset_name: str, estimated_size: int, limit: int = 5) -> str:
    """Build optimized sample query based on table size.

    Args:
        dataset_name: Name of the dataset/table
        estimated_size: Estimated row count from metadata
        limit: Number of distinct rows to return

    Returns:
        SQL query string
    """
    if not should_use_sampling(estimated_size):
        logger.debug(
            f"[{dataset_name}] Small dataset detected ({estimated_size} rows). "
            "Using standard nested query logic."
        )
        return f"""
        SELECT DISTINCT * FROM (
            SELECT * FROM {dataset_name} LIMIT 200000
        )
        LIMIT {limit}
        """
    else:
        pct_str = calculate_sampling_percentage(estimated_size)

        logger.debug(
            f"[{dataset_name}] Large dataset detected ({estimated_size} rows). "
            f"Sampling {pct_str}% (system) to retrieve approx {settings.TARGET_ROWS} rows."
        )

        return f"""
        SELECT DISTINCT * FROM {dataset_name}
        USING SAMPLE {pct_str}% (system)
        LIMIT {limit}
        """


async def generate_summary(
    dataset_name: str,
    limit: int = 5,
    org_id: Optional[str] = None,
) -> tuple[DatasetSummary, SQL_RESPONSE_TYPE]:
    """Generate dataset summary from Gopie API.

    Args:
        dataset_name: Name of the dataset
        limit: Number of sample rows to fetch
        org_id: Optional organization ID for multi-tenant support

    Returns:
        Tuple of DatasetSummary and sample data
    """
    client = GopieClient(org_id=org_id)
    path = f"/v1/api/summary/{dataset_name}?source=oltp"

    estimated_size = await get_table_estimated_size(dataset_name, org_id=org_id)
    sample_values_query = _build_sample_query(dataset_name, estimated_size, limit)
    sample_data = await execute_sql(query=sample_values_query, org_id=org_id)

    async with await client.get(path) as response:
        data = await response.json()

    if isinstance(data.get("summary"), dict) and "summary" in data["summary"]:
        data["summary"] = data["summary"]["summary"]

    return DatasetSummary(**data), sample_data
