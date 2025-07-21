from langchain_core.tools import tool
from pydantic import BaseModel


class ResultPathsSchema(BaseModel):
    """
    Use this to return the paths to the json files created by the agent, after visualization
    """

    visualization_result_paths: list[str]


@tool
def result_paths(visualization_result_paths: list[str]):
    """Use this to return the paths to the json files created by the agent, after visualization.

    Args:
        visualization_result_paths: A list of paths to the json files containing the visualizations.
    """  # noqa: E501
    return {"visualization_result_paths": visualization_result_paths}


def get_dynamic_tool_text(args: dict) -> str:
    return "Finalizing visualization results"


__tool__ = result_paths
__tool_category__ = "Data Visualization"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
