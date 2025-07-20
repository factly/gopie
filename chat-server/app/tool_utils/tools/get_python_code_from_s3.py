from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.workflow.graph.visualize_data_graph.utils import get_python_code_from_paths


@tool
async def get_python_code_from_s3(
    json_s3_paths: list[str],
    config: RunnableConfig,
):
    """
    Get the Python code files corresponding to JSON visualization config files from S3.
    The Python files have the same name as the JSON files but with .py extension.

    Args:
        json_s3_paths: List of S3 URLs for JSON config files

    Returns:
        Dictionary with Python code strings for each path
    """
    python_codes = await get_python_code_from_paths(json_s3_paths)

    result = {}
    for i, (path, code) in enumerate(zip(json_s3_paths, python_codes)):
        result[f"python_code_{i}"] = {
            "source_path": path,
            "code": code if code else "No Python code found for this visualization"
        }

    return {
        "python_codes": result
    }


def get_dynamic_tool_text(args: dict) -> str:
    return "Getting Python code from previous visualizations..."


__tool__ = get_python_code_from_s3
__tool_category__ = "Data Visualization"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
