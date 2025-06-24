"""
Tool Registration System

To add a new tool: Create a Python file in this directory with a `__tool__` attribute containing a StructuredTool instance.
Optionally define `__tool_category__` and `__get_dynamic_tool_text__` for enhanced functionality.
"""

import importlib
import pkgutil
from pathlib import Path

from langchain_core.tools import StructuredTool

# Automatically discover and import all tool modules in this directory
package_dir = Path(__file__).parent
for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
    if module_name != "__init__":
        importlib.import_module(f".{module_name}", __package__)

# Registry for all discovered tools
TOOLS: dict[str, StructuredTool] = {}
TOOL_METADATA: dict[str, dict] = {}

for module_name in list(locals()):
    module = locals()[module_name]
    # Check if module defines a tool (has __tool__ attribute)
    if hasattr(module, "__tool__"):
        tool: StructuredTool = module.__tool__
        tool_name = tool.name

        tool_category = getattr(module, "__tool_category__", tool_name)

        TOOLS[tool_name] = tool

        TOOL_METADATA[tool_name] = {
            "tool_category": tool_category,
            "get_dynamic_tool_text": getattr(
                module, "__get_dynamic_tool_text__", None
            ),
        }

__all__ = ["TOOLS", "TOOL_METADATA"]
