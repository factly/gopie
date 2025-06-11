from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.workflow.graph.visualize_data_graph import visualize_data_graph


async def visualization_adapter(state: Any, config: RunnableConfig) -> dict:
    """
    Adapter node that invokes the visualization graph with properly
    formatted state and returns the result.
    The visualization graph focuses only on generating visualization data,
    not text responses.
    """
    visualization_data = state.get("visualization_data", [])

    viz_state = {
        "messages": [HumanMessage(content=state.get("query", ""))],
        "visualization_data": visualization_data,
        "user_query": state.get("query", ""),
    }

    viz_result = await visualize_data_graph.ainvoke(viz_state, config)

    formatted_data = viz_result.get("formatted_data_for_visualization")
    visualization_type = viz_result.get("visualization_type")

    response_data = {
        "visualization_data": formatted_data,
        "visualization_type": visualization_type,
        "user_query": state.get("query", ""),
    }

    return {
        "visualization_result": response_data,
    }
