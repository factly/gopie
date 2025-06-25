"""
Tool Registration System

To add a new tool: Create a Python file in this directory with a `__tool__` attribute containing a StructuredTool instance.
Optionally define `__tool_category__` and `__get_dynamic_tool_text__` for enhanced functionality, and `__should_display_tool__` to control visibility.
Finally, add the tool to the `ToolNames` enum.
"""

import importlib
from enum import Enum
from typing import Any, List, Tuple

from langchain_core.tools import StructuredTool


class ToolNames(Enum):
    EXECUTE_SQL_QUERY = "execute_sql_query"
    GET_TABLE_SCHEMA = "get_table_schema"
    LIST_DATASETS = "list_datasets"
    PLAN_SQL_QUERY = "plan_sql_query"
    RUN_PYTHON_CODE = "run_python_code"
    RESULT_PATHS = "result_paths"


def get_tool(
    tool_name: ToolNames,
) -> Tuple[str, StructuredTool, dict[str, Any]] | Tuple[None, None, None]:
    module_name = tool_name.value
    module = importlib.import_module(f"{__package__}.{module_name}")
    if hasattr(module, "__tool__"):
        tool: StructuredTool = module.__tool__
        tool_func_name = tool.name

        tool_category = getattr(module, "__tool_category__", tool_func_name)
        metadata = {
            "tool_category": tool_category,
            "get_dynamic_tool_text": getattr(
                module, "__get_dynamic_tool_text__", None
            ),
            "should_display_tool": getattr(
                module, "__should_display_tool__", False
            ),
        }

        return tool_func_name, tool, metadata
    return None, None, None


def get_tools(
    tool_names: List[ToolNames],
) -> dict[str, Tuple[StructuredTool, dict[str, Any]]]:
    tools = {}
    for tool_name in tool_names:
        tool_func_name, tool, metadata = get_tool(tool_name)
        if tool_func_name and tool and metadata:
            tools[tool_func_name] = (tool, metadata)
    return tools
