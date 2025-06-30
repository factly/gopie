"""Tests for prompts functionality."""

from unittest.mock import Mock, patch

import pytest

from app.utils.langsmith.prompt_manager import PromptManager, get_prompt
from app.workflow.prompts.prompt_selector import PromptSelector


class TestPromptSelector:
    """Test cases for PromptSelector class."""

    @pytest.fixture
    def prompt_selector(self):
        """Create a PromptSelector instance."""
        return PromptSelector()

    def test_prompt_selector_initialization(self, prompt_selector):
        """Test PromptSelector initialization."""
        assert isinstance(prompt_selector.prompt_map, dict)
        assert isinstance(prompt_selector.format_prompt_input_map, dict)

        # Check that key prompt types are in the map
        expected_prompts = [
            "plan_query",
            "identify_datasets",
            "analyze_query",
            "generate_subqueries",
            "generate_result",
            "process_query",
            "response",
        ]

        for prompt_name in expected_prompts:
            assert prompt_name in prompt_selector.prompt_map

    def test_get_prompt_with_formatting(self, prompt_selector):
        """Test getting a prompt that requires input formatting."""
        with patch.object(
            prompt_selector, "format_prompt_input"
        ) as mock_format:
            mock_format.return_value = {"input": "formatted input"}
            mock_prompt_func = Mock(return_value=["mock", "messages"])
            prompt_selector.prompt_map["plan_query"] = mock_prompt_func

            result = prompt_selector.get_prompt(
                "plan_query", user_query="test query", datasets_info={}
            )

            mock_format.assert_called_once_with(
                "plan_query", user_query="test query", datasets_info={}
            )
            mock_prompt_func.assert_called_once_with("formatted input")
            assert result == ["mock", "messages"]

    def test_get_prompt_without_formatting(self, prompt_selector):
        """Test getting a prompt that doesn't require input formatting."""
        with patch.object(
            prompt_selector, "format_prompt_input"
        ) as mock_format:
            mock_format.return_value = None
            mock_prompt_func = Mock(return_value=["mock", "messages"])
            prompt_selector.prompt_map["analyze_query"] = mock_prompt_func

            result = prompt_selector.get_prompt(
                "analyze_query",
                user_query="test query",
                tool_results="results",
            )

            mock_format.assert_called_once_with(
                "analyze_query",
                user_query="test query",
                tool_results="results",
            )
            mock_prompt_func.assert_called_once_with(
                user_query="test query", tool_results="results"
            )
            assert result == ["mock", "messages"]

    def test_get_prompt_invalid_node(self, prompt_selector):
        """Test getting a prompt for invalid node name."""
        with pytest.raises(ValueError, match="No prompt available for node"):
            prompt_selector.get_prompt("invalid_node")

    def test_format_prompt_input_with_formatter(self, prompt_selector):
        """Test format_prompt_input when formatter exists."""
        mock_formatter = Mock(return_value={"formatted": "data"})
        prompt_selector.format_prompt_input_map["plan_query"] = mock_formatter

        result = prompt_selector.format_prompt_input(
            "plan_query", user_query="test", datasets_info={}
        )

        mock_formatter.assert_called_once_with(
            user_query="test", datasets_info={}
        )
        assert result == {"formatted": "data"}

    def test_format_prompt_input_without_formatter(self, prompt_selector):
        """Test format_prompt_input when no formatter exists."""
        result = prompt_selector.format_prompt_input("analyze_query")

        assert result is None


class TestPromptManager:
    """Test cases for PromptManager class."""

    @pytest.fixture
    def prompt_manager(self):
        """Create a PromptManager instance."""
        return PromptManager()

    def test_is_langsmith_enabled_true(self, prompt_manager):
        """Test is_langsmith_enabled when enabled."""
        with patch(
            "app.utils.langsmith.prompt_manager.settings"
        ) as mock_settings:
            mock_settings.LANGSMITH_PROMPT = True

            assert prompt_manager.is_langsmith_enabled() is True

    def test_is_langsmith_enabled_false(self, prompt_manager):
        """Test is_langsmith_enabled when disabled."""
        with patch(
            "app.utils.langsmith.prompt_manager.settings"
        ) as mock_settings:
            mock_settings.LANGSMITH_PROMPT = False

            assert prompt_manager.is_langsmith_enabled() is False

    def test_get_prompt_langsmith_enabled_with_formatting(
        self, prompt_manager
    ):
        """Test get_prompt when LangSmith is enabled and input formatting is needed."""
        with (
            patch.object(
                prompt_manager, "is_langsmith_enabled", return_value=True
            ),
            patch(
                "app.utils.langsmith.prompt_manager.PromptSelector"
            ) as mock_selector_class,
            patch(
                "app.utils.langsmith.prompt_manager.pull_prompt"
            ) as mock_pull,
        ):

            mock_selector = Mock()
            mock_selector.format_prompt_input.return_value = {
                "input": "formatted"
            }
            mock_selector_class.return_value = mock_selector

            mock_langsmith_prompt = Mock()
            mock_langsmith_prompt.format_messages.return_value = [
                "langsmith",
                "messages",
            ]
            mock_pull.return_value = mock_langsmith_prompt

            result = prompt_manager.get_prompt(
                "plan_query", user_query="test", datasets_info={}
            )

            mock_pull.assert_called_once_with("plan_query")
            mock_langsmith_prompt.format_messages.assert_called_once_with(
                input="formatted"
            )
            assert result == ["langsmith", "messages"]

    def test_get_prompt_langsmith_enabled_without_formatting(
        self, prompt_manager
    ):
        """Test get_prompt when LangSmith is enabled but no input formatting."""
        with (
            patch.object(
                prompt_manager, "is_langsmith_enabled", return_value=True
            ),
            patch(
                "app.utils.langsmith.prompt_manager.PromptSelector"
            ) as mock_selector_class,
            patch(
                "app.utils.langsmith.prompt_manager.pull_prompt"
            ) as mock_pull,
        ):

            mock_selector = Mock()
            mock_selector.format_prompt_input.return_value = None
            mock_selector_class.return_value = mock_selector

            mock_langsmith_prompt = Mock()
            mock_langsmith_prompt.format_messages.return_value = [
                "langsmith",
                "messages",
            ]
            mock_pull.return_value = mock_langsmith_prompt

            result = prompt_manager.get_prompt(
                "analyze_query", user_query="test"
            )

            mock_langsmith_prompt.format_messages.assert_called_once_with(
                user_query="test"
            )
            assert result == ["langsmith", "messages"]

    def test_get_prompt_langsmith_error_fallback(self, prompt_manager):
        """Test get_prompt falls back when LangSmith fails."""
        with (
            patch.object(
                prompt_manager, "is_langsmith_enabled", return_value=True
            ),
            patch.object(
                prompt_manager,
                "get_fallback_prompt",
                return_value=["fallback"],
            ) as mock_fallback,
            patch(
                "app.utils.langsmith.prompt_manager.PromptSelector"
            ) as mock_selector_class,
            patch(
                "app.utils.langsmith.prompt_manager.pull_prompt"
            ) as mock_pull,
        ):

            mock_selector = Mock()
            mock_selector.format_prompt_input.return_value = None
            mock_selector_class.return_value = mock_selector

            mock_pull.side_effect = Exception("LangSmith error")

            result = prompt_manager.get_prompt("plan_query", user_query="test")

            mock_fallback.assert_called_once_with(
                "plan_query", user_query="test"
            )
            assert result == ["fallback"]

    def test_get_prompt_langsmith_disabled(self, prompt_manager):
        """Test get_prompt when LangSmith is disabled."""
        with (
            patch.object(
                prompt_manager, "is_langsmith_enabled", return_value=False
            ),
            patch.object(
                prompt_manager,
                "get_fallback_prompt",
                return_value=["fallback"],
            ) as mock_fallback,
        ):

            result = prompt_manager.get_prompt(
                "plan_query", user_query="test", datasets_info={}
            )

            mock_fallback.assert_called_once_with(
                "plan_query", user_query="test", datasets_info={}
            )
            assert result == ["fallback"]

    def test_get_fallback_prompt(self, prompt_manager):
        """Test get_fallback_prompt method."""
        with patch(
            "app.utils.langsmith.prompt_manager.PromptSelector"
        ) as mock_selector_class:
            mock_selector = Mock()
            mock_selector.get_prompt.return_value = ["fallback", "messages"]
            mock_selector_class.return_value = mock_selector

            result = prompt_manager.get_fallback_prompt(
                "plan_query", user_query="test"
            )

            mock_selector.get_prompt.assert_called_once_with(
                "plan_query", user_query="test"
            )
            assert result == ["fallback", "messages"]


class TestPromptUtilities:
    """Test cases for prompt utility functions."""

    def test_get_prompt_function(self):
        """Test the standalone get_prompt function."""
        with patch(
            "app.utils.langsmith.prompt_manager.PromptManager"
        ) as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_prompt.return_value = ["test", "messages"]
            mock_manager_class.return_value = mock_manager

            result = get_prompt("plan_query", user_query="test")

            mock_manager.get_prompt.assert_called_once_with(
                "plan_query", user_query="test"
            )
            assert result == ["test", "messages"]


class TestSpecificPrompts:
    """Test cases for specific prompt implementations."""

    def test_response_prompt_creation(self):
        """Test response prompt creation."""
        from app.workflow.prompts.response_prompt import (
            create_response_prompt,
            format_response_input,
        )

        result = create_response_prompt("Test input")

        assert len(result) == 2
        assert result[0].content  # SystemMessage should have content
        assert result[1].content == "Test input"  # HumanMessage content

    def test_response_prompt_input_formatting(self):
        """Test response prompt input formatting."""

        query_result = {
            "successful_results": [
                {
                    "data": [{"name": "John", "age": 25}],
                    "explanation": "User data",
                }
            ],
            "failed_results": [
                {
                    "sql_query": "SELECT * FROM invalid",
                    "error": "Table not found",
                }
            ],
        }

        result = format_response_input(query_result)

        assert "input" in result
        assert (
            "User data" in result["input"]
            or "Error occurred" in result["input"]
        )
        assert "FAILED QUERIES" in result["input"]
        assert "Table not found" in result["input"]

    def test_plan_query_prompt_creation(self):
        """Test plan query prompt creation."""
        from app.workflow.prompts.plan_query_prompt import (
            create_plan_query_prompt,
            format_plan_query_input,
        )

        result = create_plan_query_prompt("Test planning input")

        assert len(result) == 2
        assert result[0].content  # SystemMessage
        assert result[1].content  # HumanMessage

    def test_plan_query_input_formatting(self):
        """Test plan query input formatting."""
        from app.workflow.prompts.plan_query_prompt import (
            format_plan_query_input,
        )

        result = format_plan_query_input(
            user_query="Show me sales data",
            datasets_info={
                "dataset1": {"name": "sales", "columns": ["id", "amount"]}
            },
            error_messages=[{"validation": "Invalid column"}],
            retry_count=1,
        )

        assert "input" in result
        assert "Show me sales data" in result["input"]
        assert "sales" in result["input"]
        assert "PREVIOUS ERRORS" in result["input"]
        assert "Invalid column" in result["input"]

    def test_analyze_query_prompt_creation(self):
        """Test analyze query prompt creation."""
        from app.workflow.prompts.analyze_query_prompt import (
            create_analyze_query_prompt,
        )

        result = create_analyze_query_prompt(
            user_query="Test query",
            tool_results="Tool output",
            tool_call_count=2,
            dataset_ids=["ds1"],
            project_ids=["proj1"],
        )

        assert len(result) == 2
        assert "Test query" in result[1].content
        assert "Tool output" in result[1].content
        assert "2/5" in result[1].content  # Tool call count

    def test_generate_result_prompt_creation(self):
        """Test generate result prompt creation."""
        from app.workflow.prompts.generate_result_prompt import (
            create_generate_result_prompt,
        )

        result = create_generate_result_prompt("Result generation input")

        assert len(result) == 2
        assert result[0].content  # Long system message
        assert "Result generation input" in result[1].content

    def test_identify_datasets_prompt_creation(self):
        """Test identify datasets prompt creation."""
        from app.workflow.prompts.identify_datasets_prompt import (
            create_identify_datasets_prompt,
        )

        result = create_identify_datasets_prompt(
            "Dataset identification input"
        )

        assert len(result) == 2
        assert result[0].content  # System message
        assert "Dataset identification input" in result[1].content

    def test_process_query_prompt_creation(self):
        """Test process query prompt creation."""
        from app.workflow.prompts.process_query_prompt import (
            create_process_query_prompt,
        )

        result = create_process_query_prompt("SQL processing input")

        assert len(result) == 2
        assert "DuckDB" in result[0].content  # Should mention DuckDB
        assert "SQL processing input" in result[1].content


class TestPromptIntegration:
    """Integration tests for prompt system."""

    def test_end_to_end_prompt_retrieval(self):
        """Test complete prompt retrieval flow."""
        with patch(
            "app.utils.langsmith.prompt_manager.settings"
        ) as mock_settings:
            mock_settings.LANGSMITH_PROMPT = False

            # Test with fallback (LangSmith disabled)
            result = get_prompt(
                "response", query_result={"successful_results": []}
            )

            assert result is not None
            assert len(result) == 2  # SystemMessage + HumanMessage

    def test_prompt_selector_all_prompts_accessible(self):
        """Test that all defined prompts are accessible."""
        selector = PromptSelector()

        # Test that all NodeName enum values have corresponding prompts
        for node_name in [
            "plan_query",
            "identify_datasets",
            "analyze_query",
            "generate_subqueries",
            "generate_result",
            "process_query",
            "response",
            "check_visualization",
        ]:
            assert node_name in selector.prompt_map
            # Should not raise an exception
            prompt_func = selector.prompt_map[node_name]
            assert callable(prompt_func)

    def test_prompt_formatting_consistency(self):
        """Test that prompt formatting works consistently."""
        selector = PromptSelector()

        # Test prompts that should have formatters
        prompts_with_formatters = [
            "generate_result",
            "identify_datasets",
            "plan_query",
            "process_query",
            "response",
            "sql_query_planning",
        ]

        for prompt_name in prompts_with_formatters:
            assert prompt_name in selector.format_prompt_input_map
            formatter = selector.format_prompt_input_map[prompt_name]
            assert callable(formatter)
