"""Abstract base class for OLAP query builders."""

from abc import ABC, abstractmethod


class OlapQueryBuilder(ABC):
    """Abstract base class for OLAP-specific query builders.

    Implementations provide database-specific SQL generation for:
    - Table size estimation
    - Data sampling
    - Fuzzy string matching (Levenshtein)
    - Pattern matching (ILIKE)
    """

    @abstractmethod
    def get_db_type(self) -> str:
        """Return the database type identifier (e.g., 'duckdb', 'clickhouse')."""
        pass

    @abstractmethod
    def get_estimated_size_query(self, table_name: str) -> str:
        """Return query to get estimated row count for a table."""
        pass

    @abstractmethod
    def build_sample_query(self, table_name: str, pct: str, limit: int) -> str:
        """Return query with sampling for large tables."""
        pass

    @abstractmethod
    def build_small_table_query(self, table_name: str, limit: int) -> str:
        """Return query for small tables without sampling."""
        pass

    @abstractmethod
    def build_levenshtein_query(
        self, table_name: str, column_name: str, value: str, limit: int
    ) -> str:
        """Return fuzzy matching query using Levenshtein distance."""
        pass

    @abstractmethod
    def build_ilike_query(self, table_name: str, column_name: str, value: str, limit: int) -> str:
        """Return case-insensitive pattern matching query."""
        pass

    @abstractmethod
    def build_large_table_ilike_query(
        self, table_name: str, column_name: str, value: str, pct: str, limit: int
    ) -> str:
        """Return case-insensitive pattern matching query for large tables with sampling."""
        pass

    @abstractmethod
    def build_large_table_levenshtein_query(
        self, table_name: str, column_name: str, value: str, pct: str, limit: int
    ) -> str:
        """Return fuzzy matching query for large tables with sampling."""
        pass
