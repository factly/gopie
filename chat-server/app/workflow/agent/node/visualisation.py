from langchain_core.runnables import RunnableConfig

from app.workflow.graph.visualize_data_graph.graph import (
    graph as visualize_data_graph,
)
from langgraph.graph import END

from ..types import AgentState


async def call_visualization_agent(state: AgentState, config: RunnableConfig) -> AgentState | None:
    """
    Invoke the visualization agent to process the user query and datasets.

    This function asynchronously calls the data graph visualization agent using the current user query and datasets from the agent state. It does not return a value.
    """
    input_state = {
        "user_query": state.get("user_query", ""),
        "datasets": state.get("datasets", []),
        "prev_csv_paths": state.get("prev_csv_paths", []),
    }

    _ = await visualize_data_graph.ainvoke(input_state, config=config)  # type: ignore


async def should_run_visualization(state: AgentState):
    """
    Determine the next workflow step based on whether visualization is needed and datasets are available.
    """
    if state.get("needs_visualization", False) and state.get("datasets", []):
        return "visualization_agent"
    else:
        return END
