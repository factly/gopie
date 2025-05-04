import importlib
import pkgutil
from pathlib import Path

from langchain_core.tools import StructuredTool

package_dir = Path(__file__).parent
for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
    if module_name != "__init__":
        importlib.import_module(f".{module_name}", __package__)

TOOLS: dict[str, StructuredTool] = {}

for module_name in list(locals()):
    module = locals()[module_name]
    if hasattr(module, "__tool__"):
        tool: StructuredTool = module.__tool__
        TOOLS[tool.name] = tool

__all__ = ["TOOLS"]
