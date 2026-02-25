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

    async def fake_execute_sql(query: str, org_id=None, user_id=None):
        captured_query["query"] = query
        return [
            {"name": "Finance"},
            {"name": "Financial Services"},
        ]

    monkeypatch.setattr("app.utils.graph_utils.column_value_matching.execute_sql", fake_execute_sql)

    similar_values, match_source, error_message = await find_similar_values(
        "fin", "name", "employees", org_id="test_org", user_id="test_user"
    )

    assert similar_values == ["Finance", "Financial Services"]
    # Ensure LIKE path used (no levenshtein in query)
    assert "levenshtein(" not in captured_query["query"]


@pytest.mark.asyncio
async def test_find_similar_values_falls_back_to_levenshtein(monkeypatch):
    """Test fallback to Levenshtein when ILIKE returns empty results."""
    calls = {"count": 0}

    async def fake_execute_sql(query: str, org_id=None, user_id=None):
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
        "Alice", "name", "users", org_id="test_org", user_id="test_user"
    )

    assert similar_values == ["Alison", "Alicia"]
    # Called twice: LIKE path then Levenshtein
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_find_similar_values_handles_errors_and_returns_empty(monkeypatch):
    """Test that both ILIKE and Levenshtein failures result in empty list return."""

    async def fake_execute_sql(query: str, org_id=None, user_id=None):
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
        "foo", "name", "t", org_id="test_org", user_id="test_user"
    )

    # Both LIKE and Levenshtein will raise; function should still return []
    assert similar_values == []


@pytest.mark.asyncio
async def test_verify_fuzzy_values_appends_suggestions(monkeypatch):
    """Test that fuzzy value verification appends suggestions correctly."""

    async def fake_execute_sql(query: str, org_id=None, user_id=None):
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
        org_id="test_org",
        user_id="test_user",
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
