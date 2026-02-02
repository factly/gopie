"""
Unit tests for OLAP query builders.

These tests verify the database-specific SQL query generation for DuckDB and ClickHouse.
Uses table-driven tests with @pytest.mark.parametrize for comprehensive coverage.
"""

import pytest

pytestmark = pytest.mark.unit


class TestDuckDBQueryBuilder:
    """Table-driven tests for DuckDB query builder."""

    @pytest.mark.parametrize(
        "table_name,expected_contains",
        [
            ("my_table", ["duckdb_tables()", "estimated_size", "my_table"]),
            ("users", ["duckdb_tables()", "estimated_size", "users"]),
            ("gp_ABC123", ["duckdb_tables()", "estimated_size", "gp_ABC123"]),
            ("gp_wQVK8yAgmBJHe", ["duckdb_tables()", "estimated_size", "gp_wQVK8yAgmBJHe"]),
        ],
        ids=["basic_table", "users_table", "prefixed_table", "real_table_name"],
    )
    def test_estimated_size_query(self, table_name: str, expected_contains: list[str]):
        from app.utils.olap.duckdb import DuckDBQueryBuilder

        builder = DuckDBQueryBuilder()
        query = builder.get_estimated_size_query(table_name)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"

    @pytest.mark.parametrize(
        "table_name,pct,limit,expected_contains",
        [
            ("users", "0.5", 10, ["USING SAMPLE", "0.5%", "(system)", "LIMIT 10"]),
            ("data", "1.0", 5, ["USING SAMPLE", "1.0%", "(system)", "LIMIT 5"]),
            ("large_table", "0.001", 100, ["USING SAMPLE", "0.001%", "(system)", "LIMIT 100"]),
        ],
        ids=["half_percent_sample", "one_percent_sample", "tiny_sample"],
    )
    def test_sample_query(
        self, table_name: str, pct: str, limit: int, expected_contains: list[str]
    ):
        from app.utils.olap.duckdb import DuckDBQueryBuilder

        builder = DuckDBQueryBuilder()
        query = builder.build_sample_query(table_name, pct, limit)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"

    @pytest.mark.parametrize(
        "table_name,limit,expected_contains",
        [
            ("users", 10, ["LIMIT 200000", "LIMIT 10"]),
            ("data", 5, ["LIMIT 200000", "LIMIT 5"]),
        ],
        ids=["small_table_ilike", "small_table_levenshtein"],
    )
    def test_small_table_query(self, table_name: str, limit: int, expected_contains: list[str]):
        from app.utils.olap.duckdb import DuckDBQueryBuilder

        builder = DuckDBQueryBuilder()
        query = builder.build_small_table_query(table_name, limit)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"
        # Should NOT use sampling for small tables
        assert "USING SAMPLE" not in query

    @pytest.mark.parametrize(
        "table_name,column,value,limit,expected_contains",
        [
            (
                "users",
                "name",
                "john",
                5,
                ["levenshtein(", "lower(", "ORDER BY distance", "LIMIT 5", "LIMIT 200000"],
            ),
            ("data", "city", "NYC", 10, ["levenshtein(", "lower(", "LIMIT 10", "LIMIT 200000"]),
            (
                "employees",
                "department",
                "Engineering",
                3,
                ["levenshtein(", "lower(", "LIMIT 3", "LIMIT 200000"],
            ),
        ],
        ids=["name_search", "city_search", "department_search"],
    )
    def test_levenshtein_query(
        self,
        table_name: str,
        column: str,
        value: str,
        limit: int,
        expected_contains: list[str],
    ):
        from app.utils.olap.duckdb import DuckDBQueryBuilder

        builder = DuckDBQueryBuilder()
        query = builder.build_levenshtein_query(table_name, column, value, limit)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"

    @pytest.mark.parametrize(
        "table_name,column,value,limit,expected_contains",
        [
            (
                "users",
                "name",
                "john",
                5,
                ["LIKE", "LOWER(", "LIMIT 5", "LIMIT 200000"],
            ),
        ],
        ids=["ilike_search"],
    )
    def test_ilike_query(
        self,
        table_name: str,
        column: str,
        value: str,
        limit: int,
        expected_contains: list[str],
    ):
        from app.utils.olap.duckdb import DuckDBQueryBuilder

        builder = DuckDBQueryBuilder()
        query = builder.build_ilike_query(table_name, column, value, limit)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"

    def test_get_db_type(self):
        from app.utils.olap.duckdb import DuckDBQueryBuilder

        builder = DuckDBQueryBuilder()
        assert builder.get_db_type() == "duckdb"

    @pytest.mark.parametrize(
        "table_name,column,value,pct,limit,expected_contains",
        [
            pytest.param(
                "users",
                "name",
                "john",
                "0.5",
                5,
                ["USING SAMPLE", "LOWER(", "LIKE", "||", "LIMIT 5"],
                id="large_table_ilike",
            ),
            pytest.param(
                "products",
                "category",
                "Electronics",
                "0.1",
                10,
                ["USING SAMPLE", "LOWER(", "LIKE", "||", "LIMIT 10"],
                id="large_table_ilike_category",
            ),
        ],
    )
    def test_large_table_ilike_query(
        self,
        table_name: str,
        column: str,
        value: str,
        pct: str,
        limit: int,
        expected_contains: list[str],
    ):
        from app.utils.olap.duckdb import DuckDBQueryBuilder

        builder = DuckDBQueryBuilder()
        query = builder.build_large_table_ilike_query(table_name, column, value, pct, limit)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"

    @pytest.mark.parametrize(
        "table_name,column,value,pct,limit,expected_contains",
        [
            pytest.param(
                "users",
                "name",
                "john",
                "0.5",
                5,
                ["USING SAMPLE", "levenshtein(", "lower(", "ORDER BY distance", "LIMIT 5"],
                id="large_table_levenshtein",
            ),
        ],
    )
    def test_large_table_levenshtein_query(
        self,
        table_name: str,
        column: str,
        value: str,
        pct: str,
        limit: int,
        expected_contains: list[str],
    ):
        from app.utils.olap.duckdb import DuckDBQueryBuilder

        builder = DuckDBQueryBuilder()
        query = builder.build_large_table_levenshtein_query(table_name, column, value, pct, limit)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"


class TestClickHouseQueryBuilder:
    """Table-driven tests for ClickHouse query builder."""

    @pytest.mark.parametrize(
        "table_name,expected_contains,not_expected",
        [
            (
                "my_table",
                ["system.tables", "total_rows", "my_table", "database =", "currentDatabase()"],
                ["duckdb_tables"],
            ),
            (
                "users",
                ["system.tables", "total_rows", "users", "database =", "currentDatabase()"],
                ["duckdb_tables"],
            ),
            (
                "gp_wQVK8yAgmBJHe",
                [
                    "system.tables",
                    "total_rows",
                    "gp_wQVK8yAgmBJHe",
                    "database =",
                    "currentDatabase()",
                ],
                ["duckdb_tables"],
            ),
        ],
        ids=["basic_table", "users_table", "real_table_name"],
    )
    def test_estimated_size_query(
        self, table_name: str, expected_contains: list[str], not_expected: list[str]
    ):
        from app.utils.olap.clickhouse import ClickHouseQueryBuilder

        builder = ClickHouseQueryBuilder()
        query = builder.get_estimated_size_query(table_name)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"
        for not_exp in not_expected:
            assert not_exp not in query, f"Did not expect '{not_exp}' in query: {query}"

    @pytest.mark.parametrize(
        "table_name,pct,limit,expected_contains,not_expected",
        [
            (
                "users",
                "0.5",
                10,
                ["ORDER BY rand()", "LIMIT 10", "SELECT DISTINCT", "LIMIT 10000"],
                ["SAMPLE 0.", "USING SAMPLE", "(system)"],
            ),
            (
                "data",
                "1.0",
                5,
                ["ORDER BY rand()", "LIMIT 5", "SELECT DISTINCT", "LIMIT 10000"],
                ["SAMPLE 0.", "USING SAMPLE", "(system)"],
            ),
            (
                "large_table",
                "0.001",
                100,
                ["ORDER BY rand()", "LIMIT 100", "SELECT DISTINCT", "LIMIT 10000"],
                ["SAMPLE 0.", "USING SAMPLE", "(system)"],
            ),
        ],
        ids=["half_percent_sample", "one_percent_sample", "tiny_sample"],
    )
    def test_sample_query(
        self,
        table_name: str,
        pct: str,
        limit: int,
        expected_contains: list[str],
        not_expected: list[str],
    ):
        """Test that ClickHouse sampling uses ORDER BY rand() with bounded LIMIT.

        ClickHouse SAMPLE clause requires tables to have SAMPLE BY expression defined
        at creation time. Using ORDER BY rand() LIMIT n leverages ClickHouse's
        partial sort optimization (top-N algorithm) which is efficient even on TB-scale tables.
        """
        from app.utils.olap.clickhouse import ClickHouseQueryBuilder

        builder = ClickHouseQueryBuilder()
        query = builder.build_sample_query(table_name, pct, limit)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"
        for not_exp in not_expected:
            assert not_exp not in query, f"Did not expect '{not_exp}' in query: {query}"

    @pytest.mark.parametrize(
        "table_name,column,value,limit,expected_contains,not_expected",
        [
            (
                "users",
                "name",
                "john",
                5,
                ["levenshteinDistance(", "lower(", "LIMIT 5", "LIMIT 200000"],
                ["levenshtein(lower"],
            ),
            (
                "data",
                "city",
                "NYC",
                10,
                ["levenshteinDistance(", "lower(", "LIMIT 10", "LIMIT 200000"],
                ["levenshtein(lower"],
            ),
        ],
        ids=["name_search", "city_search"],
    )
    def test_levenshtein_query(
        self,
        table_name: str,
        column: str,
        value: str,
        limit: int,
        expected_contains: list[str],
        not_expected: list[str],
    ):
        from app.utils.olap.clickhouse import ClickHouseQueryBuilder

        builder = ClickHouseQueryBuilder()
        query = builder.build_levenshtein_query(table_name, column, value, limit)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"
        for not_exp in not_expected:
            assert not_exp not in query, f"Did not expect '{not_exp}' in query: {query}"

    def test_get_db_type(self):
        from app.utils.olap.clickhouse import ClickHouseQueryBuilder

        builder = ClickHouseQueryBuilder()
        assert builder.get_db_type() == "clickhouse"

    @pytest.mark.parametrize(
        "table_name,column,value,pct,limit,expected_contains,not_expected",
        [
            pytest.param(
                "users",
                "name",
                "john",
                "0.5",
                5,
                ["ORDER BY rand()", "lower(", "LIKE", "concat(", "LIMIT 5"],
                ["||"],
                id="large_table_ilike",
            ),
            pytest.param(
                "products",
                "category",
                "Electronics",
                "0.1",
                10,
                ["ORDER BY rand()", "lower(", "LIKE", "concat(", "LIMIT 10"],
                ["||"],
                id="large_table_ilike_category",
            ),
        ],
    )
    def test_large_table_ilike_query(
        self,
        table_name: str,
        column: str,
        value: str,
        pct: str,
        limit: int,
        expected_contains: list[str],
        not_expected: list[str],
    ):
        from app.utils.olap.clickhouse import ClickHouseQueryBuilder

        builder = ClickHouseQueryBuilder()
        query = builder.build_large_table_ilike_query(table_name, column, value, pct, limit)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"
        for not_exp in not_expected:
            assert not_exp not in query, f"Did not expect '{not_exp}' in query: {query}"

    @pytest.mark.parametrize(
        "table_name,column,value,pct,limit,expected_contains,not_expected",
        [
            pytest.param(
                "users",
                "name",
                "john",
                "0.5",
                5,
                ["ORDER BY rand()", "lower(", "levenshteinDistance(", "LIMIT 5"],
                ["levenshtein("],
                id="large_table_levenshtein",
            ),
        ],
    )
    def test_large_table_levenshtein_query(
        self,
        table_name: str,
        column: str,
        value: str,
        pct: str,
        limit: int,
        expected_contains: list[str],
        not_expected: list[str],
    ):
        from app.utils.olap.clickhouse import ClickHouseQueryBuilder

        builder = ClickHouseQueryBuilder()
        query = builder.build_large_table_levenshtein_query(table_name, column, value, pct, limit)
        for expected in expected_contains:
            assert expected in query, f"Expected '{expected}' in query: {query}"
        for not_exp in not_expected:
            assert not_exp not in query, f"Did not expect '{not_exp}' in query: {query}"


class TestQueryBuilderFactory:
    """Table-driven tests for query builder factory."""

    @pytest.mark.parametrize(
        "db_type,expected_builder_type",
        [
            ("duckdb", "duckdb"),
            ("motherduck", "duckdb"),
            ("motherduck_org", "duckdb"),
            ("clickhouse", "clickhouse"),
            ("clickhouse_cluster", "clickhouse"),
            ("clickhouse_org", "clickhouse"),
            ("DUCKDB", "duckdb"),  # case-insensitive
            ("ClickHouse", "clickhouse"),  # case-insensitive
            ("MOTHERDUCK", "duckdb"),  # case-insensitive
            ("unknown", "duckdb"),  # default fallback
            ("", "duckdb"),  # empty string fallback
        ],
        ids=[
            "duckdb",
            "motherduck",
            "motherduck_org",
            "clickhouse",
            "clickhouse_cluster",
            "clickhouse_org",
            "duckdb_uppercase",
            "clickhouse_mixed_case",
            "motherduck_uppercase",
            "unknown_fallback",
            "empty_fallback",
        ],
    )
    def test_get_query_builder(self, monkeypatch, db_type: str, expected_builder_type: str):
        from app.core.config import settings
        from app.utils.olap.factory import get_query_builder

        monkeypatch.setattr(settings, "OLAP_DB_TYPE", db_type)
        builder = get_query_builder()
        assert builder.get_db_type() == expected_builder_type

    @pytest.mark.parametrize(
        "db_type,expected",
        [
            ("duckdb", True),
            ("motherduck", True),
            ("motherduck_org", True),
            ("clickhouse", False),
            ("clickhouse_cluster", False),
            ("clickhouse_org", False),
            ("unknown", True),  # Defaults to DuckDB for backward compatibility
            ("", True),  # Defaults to DuckDB for backward compatibility
        ],
        ids=[
            "duckdb",
            "motherduck",
            "motherduck_org",
            "clickhouse",
            "clickhouse_cluster",
            "clickhouse_org",
            "unknown_defaults_to_duckdb",
            "empty_defaults_to_duckdb",
        ],
    )
    def test_is_duckdb_family(self, monkeypatch, db_type: str, expected: bool):
        from app.core.config import settings
        from app.utils.olap.factory import is_duckdb_family

        monkeypatch.setattr(settings, "OLAP_DB_TYPE", db_type)
        assert is_duckdb_family() == expected

    @pytest.mark.parametrize(
        "db_type,expected",
        [
            ("duckdb", False),
            ("motherduck", False),
            ("motherduck_org", False),
            ("clickhouse", True),
            ("clickhouse_cluster", True),
            ("clickhouse_org", True),
            ("unknown", False),
            ("", False),
        ],
        ids=[
            "duckdb",
            "motherduck",
            "motherduck_org",
            "clickhouse",
            "clickhouse_cluster",
            "clickhouse_org",
            "unknown",
            "empty",
        ],
    )
    def test_is_clickhouse_family(self, monkeypatch, db_type: str, expected: bool):
        from app.core.config import settings
        from app.utils.olap.factory import is_clickhouse_family

        monkeypatch.setattr(settings, "OLAP_DB_TYPE", db_type)
        assert is_clickhouse_family() == expected


class TestQueryBuilderInterface:
    """Tests to verify the query builder interface is implemented correctly."""

    def test_duckdb_implements_interface(self):
        from app.utils.olap.base import OlapQueryBuilder
        from app.utils.olap.duckdb import DuckDBQueryBuilder

        builder = DuckDBQueryBuilder()
        assert isinstance(builder, OlapQueryBuilder)

    def test_clickhouse_implements_interface(self):
        from app.utils.olap.base import OlapQueryBuilder
        from app.utils.olap.clickhouse import ClickHouseQueryBuilder

        builder = ClickHouseQueryBuilder()
        assert isinstance(builder, OlapQueryBuilder)
