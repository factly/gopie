from langchain_core.tools import tool
from pydantic import BaseModel


class ResultPathsSchema(BaseModel):
    """
    Use this to return the paths to both json and png files created by the agent, after visualization
    """

    visualization_result_paths: list[str]
    visualization_png_paths: list[str]


@tool
def result_paths(
    visualization_json_paths: list[str],
    visualization_png_paths: list[str],
    status_message: str = "",
):
    """Use this to return the paths to both json and png files created by the agent, after visualization.

    Args:
        visualization_json_paths: A list of paths to the json files containing the visualizations.
        visualization_png_paths: A list of paths to the png files containing the visualization images.
    """
    return {
        "visualization_json_paths": visualization_json_paths,
        "visualization_png_paths": visualization_png_paths,
    }


def get_dynamic_tool_text(args: dict) -> str:
    return args.get("status_message") or "Finalizing visualization results"


__tool__ = result_paths
__tool_category__ = "Data Visualization"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
