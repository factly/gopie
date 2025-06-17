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
    viz_data = state.get("viz_data", [])

    viz_state = {
        "messages": [HumanMessage(content=state.get("query", ""))],
        "viz_data": viz_data,
        "user_query": state.get("query", ""),
    }

    viz_result = await visualize_data_graph.ainvoke(viz_state, config)

    formatted_viz_data = viz_result.get("formatted_viz_data")
    viz_type = viz_result.get("viz_type")

    response_data = {
        "viz_result": formatted_viz_data,
        "viz_type": viz_type,
        "user_query": state.get("query", ""),
    }

    return {
        "viz_result": response_data,
    }
