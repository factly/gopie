"""Tests for tools utility functionality."""

from enum import Enum
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.tool_utils.tools import ToolNames, get_tool, get_tools
from app.tool_utils.tools.run_python_code import (
    get_dynamic_tool_text,
    run_python_code,
)


class TestToolNames:
    """Test cases for ToolNames enum."""

    def test_tool_names_enum_values(self):
        """Test that ToolNames enum has expected values."""
        expected_tools = {
            "EXECUTE_SQL_QUERY": "execute_sql_query",
            "GET_TABLE_SCHEMA": "get_table_schema",
            "LIST_DATASETS": "list_datasets",
            "PLAN_SQL_QUERY": "plan_sql_query",
            "RUN_PYTHON_CODE": "run_python_code",
            "RESULT_PATHS": "result_paths",
        }

        for tool_name, expected_value in expected_tools.items():
            assert hasattr(ToolNames, tool_name)
            assert getattr(ToolNames, tool_name).value == expected_value

    def test_tool_names_is_enum(self):
        """Test that ToolNames is an Enum."""
        assert isinstance(ToolNames.EXECUTE_SQL_QUERY, Enum)
        assert isinstance(ToolNames, type)


class TestGetTool:
    """Test cases for get_tool function."""

    def test_get_tool_valid_tool(self):
        """Test getting a valid tool."""
        with patch(
            "app.tool_utils.tools.importlib.import_module"
        ) as mock_import:
            mock_module = Mock()
            mock_tool = Mock()
            mock_tool.name = "test_tool"
            mock_module.__tool__ = mock_tool
            mock_module.__tool_category__ = "Test Category"
            mock_module.__get_dynamic_tool_text__ = Mock()
            mock_module.__should_display_tool__ = True
            mock_import.return_value = mock_module

            tool_func_name, tool, metadata = get_tool(
                ToolNames.EXECUTE_SQL_QUERY
            )

            assert tool_func_name == "test_tool"
            assert tool == mock_tool
            assert metadata["tool_category"] == "Test Category"
            assert metadata["get_dynamic_tool_text"] is not None
            assert metadata["should_display_tool"] is True

    def test_get_tool_with_defaults(self):
        """Test getting a tool with default metadata values."""
        with patch(
            "app.tool_utils.tools.importlib.import_module"
        ) as mock_import:
            mock_module = Mock()
            mock_tool = Mock()
            mock_tool.name = "test_tool"
            mock_module.__tool__ = mock_tool
            # Only required attribute, others should default
            mock_import.return_value = mock_module

            tool_func_name, tool, metadata = get_tool(
                ToolNames.EXECUTE_SQL_QUERY
            )

            assert tool_func_name == "test_tool"
            assert tool == mock_tool
            assert (
                metadata["tool_category"] == "test_tool"
            )  # Defaults to tool name
            assert metadata["get_dynamic_tool_text"] is None
            assert metadata["should_display_tool"] is False

    def test_get_tool_missing_tool_attribute(self):
        """Test getting a tool when module has no __tool__ attribute."""
        with patch(
            "app.tool_utils.tools.importlib.import_module"
        ) as mock_import:
            mock_module = Mock()
            del mock_module.__tool__  # Remove the attribute
            mock_import.return_value = mock_module

            result = get_tool(ToolNames.EXECUTE_SQL_QUERY)

            assert result == (None, None, None)

    def test_get_tool_import_error(self):
        """Test getting a tool when import fails."""
        with patch(
            "app.tool_utils.tools.importlib.import_module"
        ) as mock_import:
            mock_import.side_effect = ImportError("Module not found")

            with pytest.raises(ImportError):
                get_tool(ToolNames.EXECUTE_SQL_QUERY)


class TestGetTools:
    """Test cases for get_tools function."""

    def test_get_tools_multiple_valid_tools(self):
        """Test getting multiple valid tools."""

        def mock_get_tool(tool_name):
            if tool_name == ToolNames.EXECUTE_SQL_QUERY:
                return "execute_sql", Mock(), {"category": "SQL"}
            elif tool_name == ToolNames.RUN_PYTHON_CODE:
                return "run_python", Mock(), {"category": "Python"}
            else:
                return None, None, None

        with patch("app.tool_utils.tools.get_tool", side_effect=mock_get_tool):
            tools = get_tools(
                [ToolNames.EXECUTE_SQL_QUERY, ToolNames.RUN_PYTHON_CODE]
            )

            assert len(tools) == 2
            assert "execute_sql" in tools
            assert "run_python" in tools
            assert tools["execute_sql"][1]["category"] == "SQL"
            assert tools["run_python"][1]["category"] == "Python"

    def test_get_tools_with_invalid_tool(self):
        """Test getting tools when some are invalid."""

        def mock_get_tool(tool_name):
            if tool_name == ToolNames.EXECUTE_SQL_QUERY:
                return "execute_sql", Mock(), {"category": "SQL"}
            else:
                return None, None, None

        with patch("app.tool_utils.tools.get_tool", side_effect=mock_get_tool):
            tools = get_tools(
                [
                    ToolNames.EXECUTE_SQL_QUERY,
                    ToolNames.RUN_PYTHON_CODE,  # This will return None
                ]
            )

            assert len(tools) == 1
            assert "execute_sql" in tools

    def test_get_tools_empty_list(self):
        """Test getting tools with empty list."""
        tools = get_tools([])

        assert len(tools) == 0
        assert isinstance(tools, dict)

    def test_get_tools_all_invalid(self):
        """Test getting tools when all are invalid."""
        with patch(
            "app.tool_utils.tools.get_tool", return_value=(None, None, None)
        ):
            tools = get_tools([ToolNames.EXECUTE_SQL_QUERY])

            assert len(tools) == 0
            assert isinstance(tools, dict)


class TestRunPythonCodeTool:
    """Test cases for run_python_code tool."""

    @pytest.mark.asyncio
    async def test_run_python_code_success(self):
        """Test successful python code execution."""
        # Test the underlying function directly
        mock_sandbox = AsyncMock()
        mock_execution = Mock()
        mock_execution.logs = "Code executed successfully"
        mock_sandbox.run_code.return_value = mock_execution

        config = Mock()

        # Import and call the function directly, not through tool interface
        from app.tool_utils.tools.run_python_code import (
            run_python_code as tool_func,
        )

        result = await tool_func(
            "print('Hello, World!')",
            mock_sandbox,
            config,
        )

        mock_sandbox.run_code.assert_called_once_with("print('Hello, World!')")
        assert result == "Code executed successfully"

    @pytest.mark.asyncio
    async def test_run_python_code_with_visualization(self):
        """Test python code execution with visualization."""
        mock_sandbox = AsyncMock()
        mock_execution = Mock()
        mock_execution.logs = "Chart saved to chart.json"
        mock_sandbox.run_code.return_value = mock_execution

        visualization_code = """
        import altair as alt
        import pandas as pd

        data = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
        chart = alt.Chart(data).mark_circle().encode(x='x', y='y')
        chart.save('chart.json')
        """

        result = await run_python_code(
            code=visualization_code, sandbox=mock_sandbox, config=Mock()
        )

        assert result == "Chart saved to chart.json"

    @pytest.mark.asyncio
    async def test_run_python_code_error_handling(self):
        """Test python code execution error handling."""
        mock_sandbox = AsyncMock()
        mock_sandbox.run_code.side_effect = Exception("Code execution failed")

        with pytest.raises(Exception, match="Code execution failed"):
            await run_python_code(
                code="invalid python code", sandbox=mock_sandbox, config=Mock()
            )

    def test_get_dynamic_tool_text(self):
        """Test get_dynamic_tool_text function."""
        args = {"code": "print('test')"}

        result = get_dynamic_tool_text(args)

        assert result == "Running python code for visualization"

    def test_run_python_code_tool_attributes(self):
        """Test that run_python_code tool has correct attributes."""
        from app.tool_utils.tools import run_python_code as tool_module

        assert hasattr(tool_module, "__tool__")
        assert hasattr(tool_module, "__tool_category__")
        assert hasattr(tool_module, "__should_display_tool__")
        assert hasattr(tool_module, "__get_dynamic_tool_text__")

        assert tool_module.__tool_category__ == "Data Visualization"
        assert tool_module.__should_display_tool__ is True
        assert tool_module.__get_dynamic_tool_text__ == get_dynamic_tool_text


class TestToolIntegration:
    """Integration tests for tool system."""

    def test_tool_registration_system(self):
        """Test that the tool registration system works end-to-end."""
        # This test verifies that actual tools can be imported and used
        with patch(
            "app.tool_utils.tools.importlib.import_module"
        ) as mock_import:
            # Mock a real tool module
            mock_module = Mock()
            mock_tool = Mock()
            mock_tool.name = "run_python_code"
            mock_module.__tool__ = mock_tool
            mock_module.__tool_category__ = "Data Visualization"
            mock_module.__should_display_tool__ = True
            mock_import.return_value = mock_module

            # Test getting individual tool
            tool_func_name, tool, metadata = get_tool(
                ToolNames.RUN_PYTHON_CODE
            )

            assert tool_func_name == "run_python_code"
            assert tool == mock_tool
            assert metadata["tool_category"] == "Data Visualization"
            assert metadata["should_display_tool"] is True

            # Test getting multiple tools
            tools = get_tools([ToolNames.RUN_PYTHON_CODE])

            assert len(tools) == 1
            assert "run_python_code" in tools
            assert tools["run_python_code"][0] == mock_tool

    def test_tool_metadata_handling(self):
        """Test that tool metadata is handled correctly."""
        with patch(
            "app.tool_utils.tools.importlib.import_module"
        ) as mock_import:
            mock_module = Mock()
            mock_tool = Mock()
            mock_tool.name = "test_tool"
            mock_module.__tool__ = mock_tool

            # Test with custom dynamic text function
            def custom_dynamic_text(args):
                return f"Custom text for {args.get('param', 'default')}"

            mock_module.__get_dynamic_tool_text__ = custom_dynamic_text
            mock_module.__tool_category__ = "Custom Category"
            mock_module.__should_display_tool__ = True
            mock_import.return_value = mock_module

            tool_func_name, tool, metadata = get_tool(
                ToolNames.EXECUTE_SQL_QUERY
            )

            assert metadata["get_dynamic_tool_text"] == custom_dynamic_text
            assert metadata["tool_category"] == "Custom Category"
            assert metadata["should_display_tool"] is True

            # Test the dynamic text function
            dynamic_text = metadata["get_dynamic_tool_text"]({"param": "test"})
            assert dynamic_text == "Custom text for test"
