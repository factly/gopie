"""
Unit tests for generate_sql_prompt formatting logic, specifically verifying column value inclusion.
"""
from typing import TypedDict
from unittest.mock import MagicMock

import pytest

from app.models.data import ColumnValueMatching
from app.models.schema import DatasetSchema
from app.workflow.graph.sql_planner_graph.types import DatasetsInfo
from app.workflow.prompts.generate_sql_prompt import format_generate_sql_input


class MockFuzzyValue(TypedDict):
    value: str
    found_in_database: bool
    confidence_score: float


class MockSuggestion(TypedDict):
    requested_value: str
    found_similar_values: bool
    similar_values: list[str]
    match_source: str
    is_relevant: bool | None
    relevance_score: float | None
    error_message: str | None


class TestGenerateSqlPromptFormatting:
    @pytest.fixture
    def mock_dataset_schema(self):
        schema = MagicMock(spec=DatasetSchema)
        schema.name = "test_dataset"
        schema.format_for_prompt.return_value = "CREATE TABLE test_table ..."
        return schema

    def test_format_generate_sql_input_basic(self, mock_dataset_schema):
        """Test basic formatting without verified column values."""
        datasets_info: DatasetsInfo = {
            "dataset_schema": mock_dataset_schema,
            "sample_data_csv": "col1,col2\nval1,val2",
            "correct_column_requirements": None,
        }

        result = format_generate_sql_input(
            user_query="select * from table",
            datasets_info=datasets_info,
        )

        assert "input" in result
        assert "SAMPLE DATA (test_dataset)" in result["input"]
        assert "VERIFIED COLUMN VALUES" not in result["input"]

    def test_format_with_verified_exact_matches(self, mock_dataset_schema):
        """Test formatting with exactly matched column values."""
        # Setup mock column analysis with verified values
        mock_col_analysis = MagicMock()
        mock_col_analysis.column_name = "department"

        # Mock VerifiedValue objects
        v1 = MagicMock()
        v1.value = "Finance"
        v1.found_in_database = True

        v2 = MagicMock()
        v2.value = "HR"
        v2.found_in_database = True

        mock_col_analysis.verified_values = [v1, v2]
        mock_col_analysis.suggested_alternatives = []

        # Setup DatasetAnalysis
        mock_ds_analysis = MagicMock()
        mock_ds_analysis.columns_analyzed = [mock_col_analysis]

        # Setup ColumnValueMatching
        mock_matching = MagicMock(spec=ColumnValueMatching)
        mock_matching.datasets = {"test_dataset": mock_ds_analysis}

        datasets_info: DatasetsInfo = {
            "dataset_schema": mock_dataset_schema,
            "correct_column_requirements": mock_matching,
        }

        result = format_generate_sql_input(
            user_query="query",
            datasets_info=datasets_info,
        )

        assert "VERIFIED COLUMN VALUES" in result["input"]
        assert "department (exact matches): Finance, HR" in result["input"]

    def test_format_with_not_found_values(self, mock_dataset_schema):
        """Test formatting with values not found in database."""
        mock_col_analysis = MagicMock()
        mock_col_analysis.column_name = "region"

        v1 = MagicMock()
        v1.value = "Atlantis"
        v1.found_in_database = False

        mock_col_analysis.verified_values = [v1]
        mock_col_analysis.suggested_alternatives = []

        mock_ds_analysis = MagicMock()
        mock_ds_analysis.columns_analyzed = [mock_col_analysis]

        mock_matching = MagicMock(spec=ColumnValueMatching)
        mock_matching.datasets = {"test_dataset": mock_ds_analysis}

        datasets_info: DatasetsInfo = {
            "dataset_schema": mock_dataset_schema,
            "correct_column_requirements": mock_matching,
        }

        result = format_generate_sql_input(
            user_query="query",
            datasets_info=datasets_info,
        )

        assert "region (not found): Atlantis" in result["input"]

    def test_format_with_suggested_alternatives(self, mock_dataset_schema):
        """Test formatting with suggested fuzzy match alternatives."""
        mock_col_analysis = MagicMock()
        mock_col_analysis.column_name = "role"
        mock_col_analysis.verified_values = []

        s1 = MagicMock()
        s1.requested_value = "adminn"
        s1.found_similar_values = True
        s1.similar_values = ["admin", "administrator"]

        mock_col_analysis.suggested_alternatives = [s1]

        mock_ds_analysis = MagicMock()
        mock_ds_analysis.columns_analyzed = [mock_col_analysis]

        mock_matching = MagicMock(spec=ColumnValueMatching)
        mock_matching.datasets = {"test_dataset": mock_ds_analysis}

        datasets_info: DatasetsInfo = {
            "dataset_schema": mock_dataset_schema,
            "correct_column_requirements": mock_matching,
        }

        result = format_generate_sql_input(
            user_query="query",
            datasets_info=datasets_info,
        )

        assert "role (alternatives for 'adminn'): admin, administrator" in result["input"]

    def test_format_with_no_alternatives_found(self, mock_dataset_schema):
        """Test formatting when no alternatives were found for a value."""
        mock_col_analysis = MagicMock()
        mock_col_analysis.column_name = "id"
        mock_col_analysis.verified_values = []

        s1 = MagicMock()
        s1.requested_value = "xyz"
        s1.found_similar_values = False
        s1.similar_values = []

        mock_col_analysis.suggested_alternatives = [s1]

        mock_ds_analysis = MagicMock()
        mock_ds_analysis.columns_analyzed = [mock_col_analysis]

        mock_matching = MagicMock(spec=ColumnValueMatching)
        mock_matching.datasets = {"test_dataset": mock_ds_analysis}

        datasets_info: DatasetsInfo = {
            "dataset_schema": mock_dataset_schema,
            "correct_column_requirements": mock_matching,
        }

        result = format_generate_sql_input(
            user_query="query",
            datasets_info=datasets_info,
        )

        assert "id (no alternatives found for 'xyz')" in result["input"]
