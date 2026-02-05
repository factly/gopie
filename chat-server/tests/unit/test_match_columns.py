"""
Unit tests for the match_columns node in the SQL planner graph.

Tests cover:
- match_columns function with multi-dataset and single-dataset info
- Retry logic and max retry limit
- Routing function behavior
- Helper functions for merging assumptions and collecting failed searches
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from app.models.data import ColumnValueMatching
from app.models.message import ErrorMessage, IntermediateStep
from app.workflow.graph.sql_planner_graph.match_columns import (
    RegenerateFuzzyValuesOutput,
    _collect_failed_searches,
    _merge_column_assumptions,
    match_columns,
    route_from_match_columns,
)

pytestmark = pytest.mark.unit


class TestMatchColumns:
    """Tests for the match_columns async function."""

    @pytest.fixture(autouse=True)
    def mock_dispatch_event(self):
        """Mock adispatch_custom_event to prevent RuntimeError and verify calls."""
        with (
            patch(
                "app.workflow.events.event_utils.adispatch_custom_event", new_callable=AsyncMock
            ) as mock1,
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns.adispatch_custom_event",
                new_callable=AsyncMock,
            ) as mock2,
        ):
            yield mock1, mock2

    @pytest.fixture
    def mock_config(self):
        return RunnableConfig(metadata={"org_id": "test-org"})

    @pytest.fixture
    def sample_column_assumptions(self):
        return [
            {
                "dataset": "employees",
                "columns": [
                    {"name": "department", "exact_values": [], "fuzzy_values": ["finance"]},
                ],
            }
        ]

    @pytest.fixture
    def sample_multi_datasets_info(self, sample_column_assumptions):
        return {
            "schemas": [],
            "column_assumptions": sample_column_assumptions,
            "correct_column_requirements": None,
        }

    @pytest.fixture
    def sample_single_dataset_info(self, sample_column_assumptions):
        return {
            "dataset_schema": MagicMock(),
            "sample_data_csv": "col1,col2\nval1,val2",
            "column_assumptions": sample_column_assumptions,
            "correct_column_requirements": None,
        }

    @pytest.mark.asyncio
    async def test_match_columns_returns_empty_when_no_datasets_info(self, mock_config):
        """Test that match_columns returns empty dict when no dataset info is provided."""
        state = {
            "user_query": "test query",
            "messages": [],
        }

        result = await match_columns(state, mock_config)

        assert result == {}

    @pytest.mark.asyncio
    async def test_match_columns_returns_empty_when_no_column_assumptions(self, mock_config):
        """Test that match_columns returns empty dict when column_assumptions is empty."""
        state = {
            "user_query": "test query",
            "messages": [],
            "multi_datasets_info": {
                "schemas": [],
                "column_assumptions": [],
                "correct_column_requirements": None,
            },
        }

        result = await match_columns(state, mock_config)

        assert result == {}

    @pytest.mark.asyncio
    async def test_match_columns_returns_empty_on_error_message(
        self, mock_config, sample_multi_datasets_info
    ):
        """Test that match_columns returns empty dict when last message is an ErrorMessage."""
        state = {
            "user_query": "test query",
            "messages": [ErrorMessage(content="Previous error")],
            "multi_datasets_info": sample_multi_datasets_info,
        }

        result = await match_columns(state, mock_config)

        assert result == {}

    @pytest.mark.asyncio
    async def test_match_columns_with_multi_datasets_info(
        self, mock_config, sample_multi_datasets_info
    ):
        """Test match_columns with multi-dataset info successfully processes column matching."""
        mock_column_mappings = MagicMock(spec=ColumnValueMatching)
        mock_column_mappings.datasets = {"employees": MagicMock(columns_analyzed=[])}

        with (
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns.match_column_values",
                new_callable=AsyncMock,
                return_value=mock_column_mappings,
            ),
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns.validate_match_relevance",
                new_callable=AsyncMock,
                return_value=mock_column_mappings,
            ),
        ):
            state = {
                "user_query": "test query",
                "messages": [],
                "multi_datasets_info": sample_multi_datasets_info,
                "match_columns_retry_count": 0,
            }

            result = await match_columns(state, mock_config)

            assert "multi_datasets_info" in result
            assert result["match_columns_retry_count"] == 0
            assert len(result["messages"]) == 1
            assert isinstance(result["messages"][0], IntermediateStep)

    @pytest.mark.asyncio
    async def test_match_columns_with_single_dataset_info(
        self, mock_config, sample_single_dataset_info
    ):
        """Test match_columns with single-dataset info successfully processes column matching."""
        mock_column_mappings = MagicMock(spec=ColumnValueMatching)
        mock_column_mappings.datasets = {"employees": MagicMock(columns_analyzed=[])}

        with (
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns.match_column_values",
                new_callable=AsyncMock,
                return_value=mock_column_mappings,
            ),
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns.validate_match_relevance",
                new_callable=AsyncMock,
                return_value=mock_column_mappings,
            ),
        ):
            state = {
                "user_query": "test query",
                "messages": [],
                "single_dataset_info": sample_single_dataset_info,
                "match_columns_retry_count": 0,
            }

            result = await match_columns(state, mock_config)

            assert "single_dataset_info" in result
            assert "multi_datasets_info" not in result
            assert result["match_columns_retry_count"] == 0

    @pytest.mark.asyncio
    async def test_match_columns_retry_on_failed_fuzzy_searches(
        self, mock_config, sample_multi_datasets_info
    ):
        """Test that match_columns triggers retry when fuzzy searches fail."""
        # Create mock column mappings with failed searches
        mock_suggestion = MagicMock()
        mock_suggestion.found_similar_values = False
        mock_suggestion.match_source = "ilike"
        mock_suggestion.is_relevant = None
        mock_suggestion.requested_value = "finance"
        mock_suggestion.error_message = None

        mock_column_analysis = MagicMock()
        mock_column_analysis.column_name = "department"
        mock_column_analysis.suggested_alternatives = [mock_suggestion]

        mock_dataset_analysis = MagicMock()
        mock_dataset_analysis.columns_analyzed = [mock_column_analysis]

        mock_column_mappings = MagicMock(spec=ColumnValueMatching)
        mock_column_mappings.datasets = {"employees": mock_dataset_analysis}

        mock_regenerate_response = RegenerateFuzzyValuesOutput(
            column_assumptions=[
                {
                    "dataset": "employees",
                    "columns": [
                        {
                            "name": "department",
                            "exact_values": [],
                            "fuzzy_values": ["fin", "financial"],
                        },
                    ],
                }
            ],
            reasoning="Trying alternative search terms",
            status_message="Retrying with alternatives",
        )

        with (
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns.match_column_values",
                new_callable=AsyncMock,
                return_value=mock_column_mappings,
            ),
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns.validate_match_relevance",
                new_callable=AsyncMock,
                return_value=mock_column_mappings,
            ),
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns._regenerate_fuzzy_values",
                new_callable=AsyncMock,
                return_value=mock_regenerate_response,
            ),
        ):
            state = {
                "user_query": "show finance department",
                "messages": [],
                "multi_datasets_info": sample_multi_datasets_info,
                "match_columns_retry_count": 0,
            }

            result = await match_columns(state, mock_config)

            assert result["match_columns_retry_count"] == 1
            assert "multi_datasets_info" in result
            assert len(result["messages"]) == 1
            assert "Retrying" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_match_columns_max_retry_limit(self, mock_config, sample_multi_datasets_info):
        """Test that match_columns stops retrying after 3 attempts."""
        # Create mock with failures
        mock_suggestion = MagicMock()
        mock_suggestion.found_similar_values = False
        mock_suggestion.match_source = "ilike"
        mock_suggestion.is_relevant = None
        mock_suggestion.requested_value = "finance"
        mock_suggestion.error_message = None

        mock_column_analysis = MagicMock()
        mock_column_analysis.column_name = "department"
        mock_column_analysis.suggested_alternatives = [mock_suggestion]

        mock_dataset_analysis = MagicMock()
        mock_dataset_analysis.columns_analyzed = [mock_column_analysis]

        mock_column_mappings = MagicMock(spec=ColumnValueMatching)
        mock_column_mappings.datasets = {"employees": mock_dataset_analysis}

        with (
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns.match_column_values",
                new_callable=AsyncMock,
                return_value=mock_column_mappings,
            ),
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns.validate_match_relevance",
                new_callable=AsyncMock,
                return_value=mock_column_mappings,
            ),
        ):
            state = {
                "user_query": "show finance department",
                "messages": [],
                "multi_datasets_info": sample_multi_datasets_info,
                "match_columns_retry_count": 3,  # Already at max
            }

            result = await match_columns(state, mock_config)

            # Should proceed without retry, setting count back to 0
            assert result["match_columns_retry_count"] == 0
            assert "multi_datasets_info" in result

    @pytest.mark.asyncio
    async def test_match_columns_error_handling(self, mock_config, sample_multi_datasets_info):
        """Test that match_columns handles exceptions gracefully."""
        # Mock logger to prevent it from potentially raising or polluting logs
        with (
            patch(
                "app.workflow.graph.sql_planner_graph.match_columns.match_column_values",
                new_callable=AsyncMock,
                side_effect=Exception("Database error"),
            ),
            patch("app.workflow.graph.sql_planner_graph.match_columns.logger") as mock_logger,
        ):
            state = {
                "user_query": "test query",
                "messages": [],
                "multi_datasets_info": sample_multi_datasets_info,
                "match_columns_retry_count": 0,
            }

            result = await match_columns(state, mock_config)

            assert result["match_columns_retry_count"] == 0
            assert len(result["messages"]) == 1
            assert isinstance(result["messages"][0], ErrorMessage)
            assert "Error analyzing dataset" in result["messages"][0].content
            assert "Database error" in result["messages"][0].content
            mock_logger.exception.assert_called_once()


class TestRouteFromMatchColumns:
    """Tests for the route_from_match_columns routing function."""

    def test_route_to_match_columns_on_retry(self):
        """Test routing back to match_columns when retry count is between 1 and 3."""
        state = {
            "multi_datasets_info": {
                "column_assumptions": [{"dataset": "test", "columns": []}],
            },
            "match_columns_retry_count": 1,
        }

        result = route_from_match_columns(state)

        assert result == "match_columns"

    def test_route_to_generate_sql_when_no_retry(self):
        """Test routing to generate_sql when retry count is 0."""
        state = {
            "multi_datasets_info": {
                "column_assumptions": None,
            },
            "match_columns_retry_count": 0,
        }

        result = route_from_match_columns(state)

        assert result == "generate_sql"

    def test_route_to_generate_sql_at_max_retry(self):
        """Test routing to generate_sql when retry count reaches 3."""
        state = {
            "multi_datasets_info": {
                "column_assumptions": [{"dataset": "test", "columns": []}],
            },
            "match_columns_retry_count": 3,
        }

        result = route_from_match_columns(state)

        assert result == "generate_sql"

    def test_route_with_single_dataset_info(self):
        """Test routing works with single_dataset_info."""
        state = {
            "single_dataset_info": {
                "column_assumptions": [{"dataset": "test", "columns": []}],
            },
            "match_columns_retry_count": 2,
        }

        result = route_from_match_columns(state)

        assert result == "match_columns"

    def test_route_with_no_column_assumptions(self):
        """Test routing to generate_sql when no column assumptions exist."""
        state = {
            "multi_datasets_info": {
                "column_assumptions": None,
            },
            "match_columns_retry_count": 1,
        }

        result = route_from_match_columns(state)

        assert result == "generate_sql"


class TestMergeColumnAssumptions:
    """Tests for the _merge_column_assumptions helper function."""

    def test_merge_replaces_failed_columns(self):
        """Test that failed column assumptions are replaced with regenerated ones."""
        existing = [
            {
                "dataset": "employees",
                "columns": [
                    {"name": "department", "exact_values": [], "fuzzy_values": ["finance"]},
                    {"name": "status", "exact_values": ["active"], "fuzzy_values": []},
                ],
            }
        ]
        regenerated = [
            {
                "dataset": "employees",
                "columns": [
                    {
                        "name": "department",
                        "exact_values": [],
                        "fuzzy_values": ["fin", "financial"],
                    },
                ],
            }
        ]
        failed_searches = {
            "employees": {
                "department": [{"value": "finance"}],
            }
        }

        result = _merge_column_assumptions(existing, regenerated, failed_searches)

        assert len(result) == 1
        assert result[0]["dataset"] == "employees"
        assert len(result[0]["columns"]) == 2
        # Department should be replaced
        dept_col = next(c for c in result[0]["columns"] if c["name"] == "department")
        assert dept_col["fuzzy_values"] == ["fin", "financial"]
        # Status should remain unchanged
        status_col = next(c for c in result[0]["columns"] if c["name"] == "status")
        assert status_col["exact_values"] == ["active"]

    def test_merge_preserves_successful_columns(self):
        """Test that successful column assumptions are preserved."""
        existing = [
            {
                "dataset": "users",
                "columns": [
                    {"name": "role", "exact_values": ["admin"], "fuzzy_values": []},
                ],
            }
        ]
        regenerated = []
        failed_searches = {}

        result = _merge_column_assumptions(existing, regenerated, failed_searches)

        assert result == existing


class TestCollectFailedSearches:
    """Tests for the _collect_failed_searches helper function."""

    def test_collect_not_found_suggestions(self):
        """Test collecting suggestions where no similar values were found."""
        mock_suggestion = MagicMock()
        mock_suggestion.found_similar_values = False
        mock_suggestion.match_source = "ilike"
        mock_suggestion.is_relevant = None
        mock_suggestion.requested_value = "finance"
        mock_suggestion.error_message = None

        mock_column_analysis = MagicMock()
        mock_column_analysis.column_name = "department"
        mock_column_analysis.suggested_alternatives = [mock_suggestion]

        mock_dataset_analysis = MagicMock()
        mock_dataset_analysis.columns_analyzed = [mock_column_analysis]

        mock_column_mappings = MagicMock()
        mock_column_mappings.datasets = {"employees": mock_dataset_analysis}

        result = _collect_failed_searches(mock_column_mappings)

        assert "employees" in result
        assert "department" in result["employees"]
        assert result["employees"]["department"] == [{"value": "finance"}]

    def test_collect_validation_failed_suggestions(self):
        """Test collecting suggestions with validation_failed match source."""
        mock_suggestion = MagicMock()
        mock_suggestion.found_similar_values = True
        mock_suggestion.match_source = "validation_failed"
        mock_suggestion.is_relevant = None
        mock_suggestion.requested_value = "admin"
        mock_suggestion.error_message = "Validation failed"

        mock_column_analysis = MagicMock()
        mock_column_analysis.column_name = "role"
        mock_column_analysis.suggested_alternatives = [mock_suggestion]

        mock_dataset_analysis = MagicMock()
        mock_dataset_analysis.columns_analyzed = [mock_column_analysis]

        mock_column_mappings = MagicMock()
        mock_column_mappings.datasets = {"users": mock_dataset_analysis}

        result = _collect_failed_searches(mock_column_mappings)

        assert "users" in result
        assert "role" in result["users"]
        assert result["users"]["role"] == [{"value": "admin", "error": "Validation failed"}]

    def test_collect_irrelevant_levenshtein_matches(self):
        """Test collecting levenshtein matches marked as irrelevant."""
        mock_suggestion = MagicMock()
        mock_suggestion.found_similar_values = True
        mock_suggestion.match_source = "levenshtein"
        mock_suggestion.is_relevant = False
        mock_suggestion.relevance_score = 30.0
        mock_suggestion.requested_value = "finanse"
        mock_suggestion.error_message = None

        mock_column_analysis = MagicMock()
        mock_column_analysis.column_name = "department"
        mock_column_analysis.suggested_alternatives = [mock_suggestion]

        mock_dataset_analysis = MagicMock()
        mock_dataset_analysis.columns_analyzed = [mock_column_analysis]

        mock_column_mappings = MagicMock()
        mock_column_mappings.datasets = {"employees": mock_dataset_analysis}

        result = _collect_failed_searches(mock_column_mappings)

        assert "employees" in result
        assert "department" in result["employees"]

    def test_collect_empty_when_all_successful(self):
        """Test that empty dict is returned when all searches succeeded."""
        mock_suggestion = MagicMock()
        mock_suggestion.found_similar_values = True
        mock_suggestion.match_source = "ilike"
        mock_suggestion.is_relevant = True
        mock_suggestion.requested_value = "finance"

        mock_column_analysis = MagicMock()
        mock_column_analysis.column_name = "department"
        mock_column_analysis.suggested_alternatives = [mock_suggestion]

        mock_dataset_analysis = MagicMock()
        mock_dataset_analysis.columns_analyzed = [mock_column_analysis]

        mock_column_mappings = MagicMock()
        mock_column_mappings.datasets = {"employees": mock_dataset_analysis}

        result = _collect_failed_searches(mock_column_mappings)

        assert result == {}
