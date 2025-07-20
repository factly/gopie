from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.workflow.graph.visualize_data_graph.utils import get_previous_visualizations_configs


@tool
async def get_results_from_csv(
    csv_paths: list[str],
    config: RunnableConfig,
):
    """
    Get the visualization json config stored in the csv files.
    """
    result_data = await get_previous_visualizations_configs(csv_paths)
    return {
        "results": result_data
    }


def get_dynamic_tool_text(args: dict) -> str:
    return "Getting visualization results for modification..."


__tool__ = get_results_from_csv
__tool_category__ = "Data Visualization"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
