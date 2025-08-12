from langchain_core.runnables import RunnableConfig
from langgraph.graph import END

from app.workflow.graph.visualize_data_graph.graph import (
    graph as visualize_data_graph,
)

from ..types import AgentState


async def call_visualization_agent(state: AgentState, config: RunnableConfig) -> AgentState | None:
    """
    Invoke the visualization agent to process the user query and datasets.

    This function asynchronously calls the data graph visualization agent using the current user query and datasets from the agent state. It does not return a value.
    """
    input_state = {
        "user_query": state["user_query"],
        "datasets": state.get("datasets", []),
        "previous_visualization_result_paths": state.get("previous_json_paths", []),
        "relevant_sql_queries": state.get("relevant_sql_queries", []),
    }

    _ = await visualize_data_graph.ainvoke(input_state, config=config)  # type: ignore


async def should_run_visualization(state: AgentState):
    """
    Determine the next workflow step based on whether visualization is needed and datasets are available.
    """
    if state.get("generate_visualization", False) and state.get("datasets", []):
        return "visualization_agent"
    else:
        return END
