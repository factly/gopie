from langchain_core.tools import tool
from pydantic import BaseModel, Field


class JsonPath(BaseModel):
    json_path: str = Field(description="The path to the visualization json file.")
    description: str = Field(description="The description of the visualization json file.")


class ResultPathsSchema(BaseModel):
    """
    Use this to return the paths to both json and png files created by the agent, after visualization
    """

    visualization_json_paths: list[JsonPath] = Field(
        description="The paths to the visualization json files."
    )
    visualization_png_paths: list[str] = Field(
        description="The paths to the visualization png files."
    )


@tool
def result_paths(
    visualization_json_paths: list[JsonPath],
    visualization_png_paths: list[str],
    status_message: str = "",
):
    """Use this to return the paths to both json and png files created by the agent, after visualization.

    Args:
        visualization_json_paths: A list of paths to the json files containing the visualizations, with the description of the visualization.
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
