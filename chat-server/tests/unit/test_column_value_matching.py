import pytest

from app.models.data import ColumnValueMatching
from app.utils.graph_utils.column_value_matching import (
    find_similar_values,
    verify_fuzzy_values,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_find_similar_values_uses_ilike_first(monkeypatch):
    captured_query = {}

    async def fake_execute_sql(query: str, org_id=None):
        captured_query["query"] = query
        return [
            {"name": "Finance"},
            {"name": "Financial Services"},
        ]

    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)

    similar_values, match_source, error_message = await find_similar_values(
        "fin", "name", "employees", estimated_size=1000
    )

    assert similar_values == ["Finance", "Financial Services"]
    # Ensure LIKE path used (no levenshtein in query)
    assert "levenshtein(" not in captured_query["query"]


@pytest.mark.asyncio
async def test_find_similar_values_falls_back_to_levenshtein(monkeypatch):
    """Test fallback to Levenshtein when ILIKE returns empty results."""
    calls = {"count": 0}

    async def fake_execute_sql(query: str, org_id=None):
        calls["count"] += 1
        # Check for both DuckDB (levenshtein) and ClickHouse (levenshteinDistance) syntax
        if "levenshtein" in query.lower():
            return [
                {"name": "Alison"},
                {"name": "Alicia"},
            ]
        return []

    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)

    similar_values, match_source, error_message = await find_similar_values(
        "Alice", "name", "users", estimated_size=1000
    )

    assert similar_values == ["Alison", "Alicia"]
    # Called twice: LIKE path then Levenshtein
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_find_similar_values_handles_errors_and_returns_empty(monkeypatch):
    """Test that both ILIKE and Levenshtein failures result in empty list return."""

    async def fake_execute_sql(query: str, org_id=None):
        raise RuntimeError("DB error")

    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)
    # Silence logger to avoid logger.exception interfering
    dummy_logger = type(
        "L",
        (),
        {
            "error": lambda *args, **kwargs: None,
            "debug": lambda *args, **kwargs: None,
            "error": lambda *args, **kwargs: None,
        },
    )()
    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.logger", dummy_logger)
    # Allow real logger; function should handle exceptions and return []

    similar_values, match_source, error_message = await find_similar_values(
        "foo", "name", "t", estimated_size=1000
    )

    # Both LIKE and Levenshtein will raise; function should still return []
    assert similar_values == []


@pytest.mark.asyncio
async def test_verify_fuzzy_values_appends_suggestions(monkeypatch):
    """Test that fuzzy value verification appends suggestions correctly."""

    async def fake_execute_sql(query: str, org_id=None):
        # Check for both DuckDB (levenshtein) and ClickHouse (levenshteinDistance) syntax
        if "levenshtein" in query.lower():
            return []
        # LIKE returns one value per fuzzy term - use case-insensitive check
        query_lower = query.lower()
        if "'blue'" in query_lower:
            return [{"color": "blueberry"}]
        if "'red'" in query_lower:
            return [{"color": "redwood"}]
        return []

    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)

    column_entry = ColumnValueMatching.ColumnAnalysis(column_name="color")

    await verify_fuzzy_values(
        column_entry=column_entry,
        column_name="color",
        fuzzy_values=["blue", "red"],
        table_name="items",
        estimated_size=1000,
    )

    assert len(column_entry.suggested_alternatives) == 2
    suggestions = column_entry.suggested_alternatives
    assert suggestions[0].requested_value == "blue"
    assert suggestions[0].found_similar_values is True
    assert suggestions[0].similar_values == ["blueberry"]
    assert suggestions[0].match_source == "ilike"
    assert suggestions[0].error_message is None
    assert suggestions[1].requested_value == "red"
    assert suggestions[1].found_similar_values is True
    assert suggestions[1].similar_values == ["redwood"]
    assert suggestions[1].match_source == "ilike"
    assert suggestions[1].error_message is None


@pytest.mark.asyncio
async def test_find_similar_values_uses_sampling_for_large_table_duckdb(monkeypatch):
    """Test that DuckDB sampling syntax is used for large tables."""
    from app.core.config import settings

    captured_query = {}

    async def fake_execute_sql(query: str, org_id=None):
        captured_query["query"] = query
        return [{"name": "Finance"}]

    # Explicitly set DuckDB mode for this test
    monkeypatch.setattr(settings, "OLAP_DB_TYPE", "duckdb")
    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)

    # Use estimated_size > 150000 (SAMPLING_THRESHOLD) to trigger sampling
    similar_values, match_source, error_message = await find_similar_values(
        "fin", "name", "large_table", estimated_size=200000
    )

    assert similar_values == ["Finance"]
    assert match_source == "ilike"
    assert error_message is None
    # Verify DuckDB sampling syntax is used
    assert "USING SAMPLE" in captured_query["query"]
    assert "(system)" in captured_query["query"]


@pytest.mark.asyncio
async def test_find_similar_values_uses_sampling_for_large_table_clickhouse(monkeypatch):
    """Test that ClickHouse sampling uses ORDER BY rand() with bounded LIMIT for large tables."""
    from app.core.config import settings

    captured_query = {}

    async def fake_execute_sql(query: str, org_id=None):
        captured_query["query"] = query
        return [{"name": "Finance"}]

    # Explicitly set ClickHouse mode for this test
    monkeypatch.setattr(settings, "OLAP_DB_TYPE", "clickhouse")
    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)

    # Use estimated_size > 150000 (SAMPLING_THRESHOLD) to trigger sampling
    similar_values, match_source, error_message = await find_similar_values(
        "fin", "name", "large_table", estimated_size=200000
    )

    assert similar_values == ["Finance"]
    assert match_source == "ilike"
    assert error_message is None
    # Verify ClickHouse uses ORDER BY rand() (leverages partial sort optimization)
    assert "ORDER BY rand()" in captured_query["query"]
    assert "USING SAMPLE" not in captured_query["query"]
    # Should not use SAMPLE clause (requires SAMPLE BY in table definition)
    assert "SAMPLE 0." not in captured_query["query"]


@pytest.mark.asyncio
async def test_find_similar_values_no_sampling_for_small_table(monkeypatch):
    """Test that sampling is NOT used for small tables (estimated_size <= SAMPLING_THRESHOLD)."""
    captured_query = {}

    async def fake_execute_sql(query: str, org_id=None):
        captured_query["query"] = query
        return [{"name": "Finance"}]

    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)

    # Use estimated_size <= 150000 (SAMPLING_THRESHOLD) to avoid sampling
    similar_values, match_source, error_message = await find_similar_values(
        "fin", "name", "small_table", estimated_size=100000
    )

    assert similar_values == ["Finance"]
    assert match_source == "ilike"
    assert error_message is None
    # Verify sampling is NOT used (USING SAMPLE should NOT be in query)
    assert "USING SAMPLE" not in captured_query["query"]
    # Should use LIMIT 200000 instead
    assert "LIMIT 200000" in captured_query["query"]


@pytest.mark.asyncio
async def test_find_similar_values_levenshtein_uses_sampling_for_large_table_duckdb(monkeypatch):
    """Test that DuckDB Levenshtein fallback uses USING SAMPLE for large tables."""
    from app.core.config import settings

    captured_query = {}

    async def fake_execute_sql(query: str, org_id=None):
        captured_query["query"] = query
        if "levenshtein(" in query:
            return [{"name": "Alison"}]
        return []

    # Explicitly set DuckDB mode
    monkeypatch.setattr(settings, "OLAP_DB_TYPE", "duckdb")
    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)

    # Use estimated_size > 150000 to trigger sampling
    similar_values, match_source, error_message = await find_similar_values(
        "Alice", "name", "large_table", estimated_size=200000
    )

    assert similar_values == ["Alison"]
    assert match_source == "levenshtein"
    assert error_message is None
    # Verify DuckDB sampling is used in Levenshtein query
    assert "levenshtein(" in captured_query["query"]
    assert "USING SAMPLE" in captured_query["query"]


@pytest.mark.asyncio
async def test_find_similar_values_levenshtein_uses_sampling_for_large_table_clickhouse(monkeypatch):
    """Test that ClickHouse Levenshtein fallback uses ORDER BY rand() for large tables."""
    from app.core.config import settings

    captured_query = {}

    async def fake_execute_sql(query: str, org_id=None):
        captured_query["query"] = query
        if "levenshteinDistance(" in query:
            return [{"name": "Alison"}]
        return []

    # Explicitly set ClickHouse mode
    monkeypatch.setattr(settings, "OLAP_DB_TYPE", "clickhouse")
    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)

    # Use estimated_size > 150000 to trigger sampling
    similar_values, match_source, error_message = await find_similar_values(
        "Alice", "name", "large_table", estimated_size=200000
    )

    assert similar_values == ["Alison"]
    assert match_source == "levenshtein"
    assert error_message is None
    # Verify ClickHouse uses ORDER BY rand() with levenshteinDistance
    assert "levenshteinDistance(" in captured_query["query"]
    assert "ORDER BY rand()" in captured_query["query"]
    assert "USING SAMPLE" not in captured_query["query"]


@pytest.mark.asyncio
async def test_find_similar_values_at_sampling_threshold(monkeypatch):
    """Test behavior exactly at the sampling threshold (150000)."""
    captured_query = {}

    async def fake_execute_sql(query: str, org_id=None):
        captured_query["query"] = query
        return [{"name": "Finance"}]

    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)

    # Use estimated_size exactly at threshold (150000) - should NOT use sampling
    similar_values, match_source, error_message = await find_similar_values(
        "fin", "name", "threshold_table", estimated_size=150000
    )

    assert similar_values == ["Finance"]
    assert match_source == "ilike"
    assert error_message is None
    # At threshold, should NOT use sampling (threshold is > 150000, not >=)
    assert "USING SAMPLE" not in captured_query["query"]
    assert "LIMIT 200000" in captured_query["query"]
