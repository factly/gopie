"""ClickHouse-specific query builder implementation."""

from app.utils.olap.base import OlapQueryBuilder


class ClickHouseQueryBuilder(OlapQueryBuilder):
    """Query builder for ClickHouse backends."""

    def get_db_type(self) -> str:
        """Return 'clickhouse' as the database type."""
        return "clickhouse"

    def get_estimated_size_query(self, table_name: str) -> str:
        """Return ClickHouse query to get row count using system.tables."""
        return f"""
            SELECT total_rows AS estimated_size
            FROM system.tables
            WHERE name = '{table_name}' AND database = currentDatabase()
        """

    def build_sample_query(self, table_name: str, pct: str, limit: int) -> str:  # noqa: ARG002
        """Return ClickHouse sampling query optimized for very large tables.

        Note: ClickHouse SAMPLE clause requires tables to have SAMPLE BY expression
        defined at creation time, which is not guaranteed for dynamically created tables.

        For optimal performance on terabyte-scale tables, we use rand() with LIMIT:
        - rand() is evaluated per-row but is extremely fast (simple PRNG)
        - LIMIT with ORDER BY rand() uses partial sort (top-N algorithm)
        - ClickHouse's vectorized execution makes this efficient even on huge tables
        - Works correctly with distributed/replicated ClickHouse clusters

        The inner LIMIT is generous to ensure we get enough rows after DISTINCT,
        but capped at 100,000 to avoid excessive memory usage on very large tables.

        Args:
            table_name: Name of the table to sample from
            pct: Percentage string (not used - we rely on LIMIT for sampling)
            limit: Number of rows to return

        Returns:
            SQL query string for random sampling
        """
        # For sampling, we use a two-stage approach:
        # 1. Inner query: Get a random subset using ORDER BY rand() with generous LIMIT
        # 2. Outer query: Apply DISTINCT and final LIMIT
        #
        # The inner_limit is set to be large enough to get diverse rows but
        # capped at 100,000 to avoid memory issues on TB-scale tables.
        # 10,000 rows is typically sufficient for getting 5-100 distinct samples.
        # Cap inner_limit to avoid excessive memory usage on large tables
        inner_limit = min(max(limit * 100, 10000), 100000)

        return f"""
        SELECT DISTINCT * FROM (
            SELECT * FROM {table_name}
            ORDER BY rand()
            LIMIT {inner_limit}
        )
        LIMIT {limit}
        """

    def build_small_table_query(self, table_name: str, limit: int) -> str:
        """Return query for small tables without sampling."""
        return f"""
        SELECT DISTINCT * FROM (
            SELECT * FROM {table_name} LIMIT 200000
        )
        LIMIT {limit}
        """

    def build_levenshtein_query(
        self, table_name: str, column_name: str, value: str, limit: int
    ) -> str:
        """Return ClickHouse Levenshtein query using levenshteinDistance() function.

        Uses a nested LIMIT 200000 subquery for safety on larger tables.
        """
        return f"""
        SELECT DISTINCT {column_name},
            levenshteinDistance(lower({column_name}), lower('{value}')) AS distance
        FROM (SELECT * FROM {table_name} LIMIT 200000)
        ORDER BY distance ASC
        LIMIT {limit}
        """

    def build_ilike_query(self, table_name: str, column_name: str, value: str, limit: int) -> str:
        """Return ClickHouse case-insensitive pattern matching query.

        Uses a nested LIMIT 200000 subquery for safety on larger tables.
        """
        return f"""
        SELECT DISTINCT {column_name}
        FROM (SELECT * FROM {table_name} LIMIT 200000)
        WHERE lower({column_name}) LIKE concat('%', lower('{value}'), '%')
        LIMIT {limit}
        """

    def build_large_table_ilike_query(
        self, table_name: str, column_name: str, value: str, pct: str, limit: int
    ) -> str:
        """Return ClickHouse ILIKE query for large tables with sampling.

        Uses ClickHouse's concat() function instead of || operator.
        """
        sample_query = self.build_sample_query(table_name, pct, limit=200000)
        return f"""
        SELECT DISTINCT {column_name}
        FROM ({sample_query})
        WHERE lower({column_name}) LIKE concat('%', lower('{value}'), '%')
        LIMIT {limit}
        """

    def build_large_table_levenshtein_query(
        self, table_name: str, column_name: str, value: str, pct: str, limit: int
    ) -> str:
        """Return ClickHouse Levenshtein query for large tables with sampling."""
        sample_query = self.build_sample_query(table_name, pct, limit=200000)
        return f"""
        SELECT DISTINCT {column_name},
            levenshteinDistance(lower({column_name}), lower('{value}')) AS distance
        FROM ({sample_query})
        ORDER BY distance ASC
        LIMIT {limit}
        """
