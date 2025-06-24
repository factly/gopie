from langgraph.graph import END, START, StateGraph

from app.models.schema import ConfigSchema

from .node.multi_dataset import call_multi_dataset_agent
from .node.single_dataset import call_single_dataset_agent
from .node.supervisor import supervisor
from .node.visualisation import call_visualization_agent, check_visualization
from .types import AgentState


async def empty_node(state, config):
    return state


async def should_visualize(state, config):
    if state.get("needs_visualization", False):
        return "visualization_agent"
    else:
        return END


graph_builder = StateGraph(AgentState, config_schema=ConfigSchema)


graph_builder.add_node(
    supervisor,
    destinations=("multi_dataset_agent", "single_dataset_agent"),
)
graph_builder.add_node("multi_dataset_agent", call_multi_dataset_agent)
graph_builder.add_node("single_dataset_agent", call_single_dataset_agent)
graph_builder.add_node("visualization_agent", call_visualization_agent)
graph_builder.add_node("check_visualization", check_visualization)
graph_builder.add_node("empty_node", empty_node)

graph_builder.add_edge(START, "supervisor")
graph_builder.add_edge(START, "check_visualization")
graph_builder.add_edge("multi_dataset_agent", "empty_node")
graph_builder.add_edge("check_visualization", "empty_node")
graph_builder.add_edge("single_dataset_agent", "empty_node")
graph_builder.add_conditional_edges(
    "empty_node",
    should_visualize,
    {
        "visualization_agent": "visualization_agent",
        END: END,
    },
)
graph_builder.add_edge("visualization_agent", END)

agent_graph = graph_builder.compile()
