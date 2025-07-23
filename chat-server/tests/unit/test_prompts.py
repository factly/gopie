from unittest.mock import Mock, patch

import pytest

from app.utils.langsmith.prompt_manager import PromptManager, get_prompt
from app.workflow.prompts.prompt_selector import PromptSelector


class TestPromptSelector:
    @pytest.fixture
    def prompt_selector(self):
        return PromptSelector()

    def test_get_prompt_with_formatting(self, prompt_selector):
        with patch.object(prompt_selector, "format_prompt_input") as mock_format:
            mock_format.return_value = {"input": "formatted input"}
            mock_prompt_func = Mock(return_value=["mock", "messages"])
            prompt_selector.prompt_map["plan_query"] = mock_prompt_func

            result = prompt_selector.get_prompt(
                "plan_query", user_query="test query", datasets_info={}
            )

            mock_format.assert_called_once_with(
                "plan_query", user_query="test query", datasets_info={}
            )
            mock_prompt_func.assert_called_once_with(input="formatted input")
            assert result == ["mock", "messages"]

    def test_get_prompt_without_formatting(self, prompt_selector):
        with patch.object(prompt_selector, "format_prompt_input") as mock_format:
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
        with pytest.raises(ValueError, match="No prompt available for node"):
            prompt_selector.get_prompt("invalid_node")

    def test_format_prompt_input_with_formatter(self, prompt_selector):
        mock_formatter = Mock(return_value={"formatted": "data"})
        prompt_selector.format_prompt_input_map["plan_query"] = mock_formatter

        result = prompt_selector.format_prompt_input(
            "plan_query", user_query="test", datasets_info={}
        )

        mock_formatter.assert_called_once_with(user_query="test", datasets_info={})
        assert result == {"formatted": "data"}

    def test_format_prompt_input_without_formatter(self, prompt_selector):
        result = prompt_selector.format_prompt_input("analyze_query")

        assert result is None


class TestPromptManager:
    @pytest.fixture
    def prompt_manager(self):
        return PromptManager()

    def test_is_langsmith_enabled_true(self, prompt_manager):
        with patch("app.utils.langsmith.prompt_manager.settings") as mock_settings:
            mock_settings.LANGSMITH_PROMPT = True

            assert prompt_manager.is_langsmith_enabled() is True

    def test_is_langsmith_enabled_false(self, prompt_manager):
        with patch("app.utils.langsmith.prompt_manager.settings") as mock_settings:
            mock_settings.LANGSMITH_PROMPT = False

            assert prompt_manager.is_langsmith_enabled() is False

    def test_get_prompt_langsmith_enabled_with_formatting(self, prompt_manager):
        with (
            patch.object(prompt_manager, "is_langsmith_enabled", return_value=True),
            patch("app.utils.langsmith.prompt_manager.PromptSelector") as mock_selector_class,
            patch("app.utils.langsmith.prompt_manager.pull_prompt") as mock_pull,
        ):

            mock_selector = Mock()
            mock_selector.format_prompt_input.return_value = {"input": "formatted"}
            mock_selector_class.return_value = mock_selector

            mock_langsmith_prompt = Mock()
            mock_langsmith_prompt.format_messages.return_value = [
                "langsmith",
                "messages",
            ]
            mock_pull.return_value = mock_langsmith_prompt

            result = prompt_manager.get_prompt("plan_query", user_query="test", datasets_info={})

            mock_pull.assert_called_once_with("plan_query")
            mock_langsmith_prompt.format_messages.assert_called_once_with(input="formatted")
            assert result == ["langsmith", "messages"]

    def test_get_prompt_langsmith_enabled_without_formatting(self, prompt_manager):
        with (
            patch.object(prompt_manager, "is_langsmith_enabled", return_value=True),
            patch("app.utils.langsmith.prompt_manager.PromptSelector") as mock_selector_class,
            patch("app.utils.langsmith.prompt_manager.pull_prompt") as mock_pull,
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

            result = prompt_manager.get_prompt("analyze_query", user_query="test")

            mock_langsmith_prompt.format_messages.assert_called_once_with(user_query="test")
            assert result == ["langsmith", "messages"]

    def test_get_prompt_langsmith_error_fallback(self, prompt_manager):
        with (
            patch.object(prompt_manager, "is_langsmith_enabled", return_value=True),
            patch.object(
                prompt_manager,
                "get_fallback_prompt",
                return_value=["fallback"],
            ) as mock_fallback,
            patch("app.utils.langsmith.prompt_manager.PromptSelector") as mock_selector_class,
            patch("app.utils.langsmith.prompt_manager.pull_prompt") as mock_pull,
        ):

            mock_selector = Mock()
            mock_selector.format_prompt_input.return_value = None
            mock_selector_class.return_value = mock_selector

            mock_pull.side_effect = Exception("LangSmith error")

            result = prompt_manager.get_prompt("plan_query", user_query="test")

            mock_fallback.assert_called_once_with("plan_query", user_query="test")
            assert result == ["fallback"]

    def test_get_prompt_langsmith_disabled(self, prompt_manager):
        with (
            patch.object(prompt_manager, "is_langsmith_enabled", return_value=False),
            patch.object(
                prompt_manager,
                "get_fallback_prompt",
                return_value=["fallback"],
            ) as mock_fallback,
        ):

            result = prompt_manager.get_prompt("plan_query", user_query="test", datasets_info={})

            mock_fallback.assert_called_once_with("plan_query", user_query="test", datasets_info={})
            assert result == ["fallback"]

    def test_get_fallback_prompt(self, prompt_manager):
        with patch("app.utils.langsmith.prompt_manager.PromptSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector.get_prompt.return_value = ["fallback", "messages"]
            mock_selector_class.return_value = mock_selector

            result = prompt_manager.get_fallback_prompt("plan_query", user_query="test")

            mock_selector.get_prompt.assert_called_once_with("plan_query", user_query="test")
            assert result == ["fallback", "messages"]


class TestPromptUtilities:
    def test_get_prompt_function(self):
        with patch("app.utils.langsmith.prompt_manager.PromptManager") as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_prompt.return_value = ["test", "messages"]
            mock_manager_class.return_value = mock_manager

            result = get_prompt("plan_query", user_query="test")

            mock_manager.get_prompt.assert_called_once_with("plan_query", user_query="test")
            assert result == ["test", "messages"]


class TestPromptDynamic:
    def test_all_prompts_in_selector(self):
        import typing

        from app.workflow.prompts.prompt_selector import (
            NodeName,
            PromptSelector,
        )

        selector = PromptSelector()
        node_names = typing.get_args(NodeName)

        for node_name in node_names:
            assert node_name in selector.prompt_map, f"Node {node_name} should be in prompt_map"
            assert callable(
                selector.prompt_map[node_name]
            ), f"Prompt for {node_name} should be callable"

    def test_prompt_return_types(self):
        from unittest.mock import Mock, patch

        from langchain_core.messages import BaseMessage
        from langchain_core.prompts import ChatPromptTemplate

        from app.workflow.prompts.prompt_selector import PromptSelector

        selector = PromptSelector()

        mock_prompt_func = Mock()
        mock_messages = [Mock(spec=BaseMessage), Mock(spec=BaseMessage)]
        mock_template = Mock(spec=ChatPromptTemplate)

        def side_effect(**kwargs):
            if kwargs.get("prompt_template", False):
                return mock_template
            return mock_messages

        mock_prompt_func.side_effect = side_effect

        with patch.dict(selector.prompt_map, {"analyze_query": mock_prompt_func}):
            # Test with prompt_template=False
            result = selector.get_prompt("analyze_query", user_query="test")
            assert result == mock_messages

            # Test with prompt_template=True
            result = selector.get_prompt_template("analyze_query")
            assert result == mock_template
