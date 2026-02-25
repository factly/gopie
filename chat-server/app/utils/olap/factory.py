"""Factory function for creating OLAP query builders."""

import logging

from app.core.config import settings
from app.utils.olap.base import OlapQueryBuilder

logger = logging.getLogger(__name__)

# Database type family constants
_DUCKDB_FAMILY = {"duckdb", "motherduck", "motherduck_org"}
_CLICKHOUSE_FAMILY = {"clickhouse", "clickhouse_cluster", "clickhouse_org"}


def get_query_builder() -> OlapQueryBuilder:
    """Return the appropriate query builder based on configured OLAP backend.

    Uses the OLAP_DB_TYPE setting from config to determine which builder to use.
    Defaults to DuckDB for backward compatibility.

    Returns:
        OlapQueryBuilder: The query builder for the configured OLAP backend.
    """
    # Import here to avoid circular imports
    from app.utils.olap.clickhouse import ClickHouseQueryBuilder
    from app.utils.olap.duckdb import DuckDBQueryBuilder

    db_type = settings.OLAP_DB_TYPE.lower() if settings.OLAP_DB_TYPE else ""

    if db_type in _CLICKHOUSE_FAMILY:
        return ClickHouseQueryBuilder()
    elif db_type in _DUCKDB_FAMILY or db_type == "":
        return DuckDBQueryBuilder()
    else:
        # Unrecognized type - log warning and default to DuckDB
        logger.warning(
            f"Unrecognized OLAP_DB_TYPE '{settings.OLAP_DB_TYPE}'. "
            f"Valid values are: {_DUCKDB_FAMILY | _CLICKHOUSE_FAMILY}. "
            "Defaulting to DuckDB for backward compatibility."
        )
        return DuckDBQueryBuilder()


def is_duckdb_family() -> bool:
    """Check if the configured OLAP backend is a DuckDB-family database.

    Returns True if DuckDB, MotherDuck, MotherDuck Org mode, or if the
    type is empty/unset (defaults to DuckDB for backward compatibility).

    This matches the behavior of get_query_builder() which defaults to
    DuckDB when OLAP_DB_TYPE is not in the ClickHouse family.
    """
    db_type = settings.OLAP_DB_TYPE.lower() if settings.OLAP_DB_TYPE else ""

    if db_type in _DUCKDB_FAMILY or db_type == "":
        return True
    elif db_type in _CLICKHOUSE_FAMILY:
        return False
    else:
        # Unrecognized type - log warning and default to DuckDB behavior
        logger.warning(
            f"Unrecognized OLAP_DB_TYPE '{settings.OLAP_DB_TYPE}'. "
            f"Valid values are: {_DUCKDB_FAMILY | _CLICKHOUSE_FAMILY}. "
            "Treating as DuckDB family for backward compatibility."
        )
        return True


def is_clickhouse_family() -> bool:
    """Check if the configured OLAP backend is a ClickHouse-family database.

    Returns:
        True if ClickHouse, ClickHouse Cluster, or ClickHouse Org mode.
    """
    db_type = settings.OLAP_DB_TYPE.lower() if settings.OLAP_DB_TYPE else ""
    return db_type in _CLICKHOUSE_FAMILY
