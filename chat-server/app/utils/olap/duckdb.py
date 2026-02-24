"""DuckDB-specific query builder implementation."""

from app.utils.olap.base import OlapQueryBuilder


class DuckDBQueryBuilder(OlapQueryBuilder):
    """Query builder for DuckDB/MotherDuck backends."""

    def get_db_type(self) -> str:
        """Return 'duckdb' as the database type."""
        return "duckdb"

    def get_estimated_size_query(self, table_name: str) -> str:
        """Return DuckDB query to get estimated row count using duckdb_tables()."""
        return f"""
            SELECT estimated_size
            FROM duckdb_tables()
            WHERE table_name = '{table_name}'
        """

    def build_sample_query(self, table_name: str, pct: str, limit: int) -> str:
        """Return DuckDB sampling query using USING SAMPLE syntax."""
        return f"""
        SELECT DISTINCT * FROM {table_name}
        USING SAMPLE {pct}% (system)
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
        """Return DuckDB Levenshtein query using levenshtein() function.

        Uses a nested LIMIT 200000 subquery for safety on larger tables.
        """
        return f"""
        SELECT DISTINCT {column_name},
            levenshtein(lower({column_name}), lower('{value}')) AS distance
        FROM (SELECT * FROM {table_name} LIMIT 200000)
        ORDER BY distance ASC
        LIMIT {limit}
        """

    def build_ilike_query(self, table_name: str, column_name: str, value: str, limit: int) -> str:
        """Return DuckDB case-insensitive pattern matching query.

        Uses a nested LIMIT 200000 subquery for safety on larger tables.
        """
        return f"""
        SELECT DISTINCT {column_name}
        FROM (SELECT * FROM {table_name} LIMIT 200000)
        WHERE LOWER({column_name}) LIKE '%' || LOWER('{value}') || '%'
        LIMIT {limit}
        """

    def build_large_table_ilike_query(
        self, table_name: str, column_name: str, value: str, pct: str, limit: int
    ) -> str:
        """Return DuckDB ILIKE query for large tables with SAMPLE clause.

        Uses DuckDB's || string concatenation operator.
        """
        sample_query = self.build_sample_query(table_name, pct, limit=200000)
        return f"""
        SELECT DISTINCT {column_name}
        FROM ({sample_query})
        WHERE LOWER({column_name}) LIKE '%' || LOWER('{value}') || '%'
        LIMIT {limit}
        """

    def build_large_table_levenshtein_query(
        self, table_name: str, column_name: str, value: str, pct: str, limit: int
    ) -> str:
        """Return DuckDB Levenshtein query for large tables with sampling."""
        sample_query = self.build_sample_query(table_name, pct, limit=200000)
        return f"""
        SELECT DISTINCT {column_name},
            levenshtein(lower({column_name}), lower('{value}')) AS distance
        FROM ({sample_query})
        ORDER BY distance ASC
        LIMIT {limit}
        """
