from langgraph.graph import END, START, StateGraph

from app.models.schema import ConfigSchema

from .node.context_processor import process_context
from .node.multi_dataset import call_multi_dataset_agent
from .node.single_dataset import call_single_dataset_agent
from .node.stream_invalid_response import stream_invalid_response
from .node.supervisor import supervisor
from .node.validate_input import validate_input, should_validate_input
from .node.visualisation import call_visualization_agent, check_visualization
from .types import AgentState


async def should_visualize(state: AgentState):
    if state.get("needs_visualization", False) and state.get("datasets", []):
        return "visualization_agent"
    else:
        return END


graph_builder = StateGraph(AgentState, config_schema=ConfigSchema)


graph_builder.add_node("validate_input", validate_input)
graph_builder.add_node("stream_invalid_response", stream_invalid_response)
graph_builder.add_node("process_context", process_context)
graph_builder.add_node(
    supervisor,
    destinations=("multi_dataset_agent", "single_dataset_agent", "visualization_agent"),
    defer=True,
)
graph_builder.add_node("multi_dataset_agent", call_multi_dataset_agent)
graph_builder.add_node("single_dataset_agent", call_single_dataset_agent)
graph_builder.add_node("visualization_agent", call_visualization_agent)
graph_builder.add_node("check_visualization", check_visualization)

graph_builder.add_conditional_edges(
    "validate_input",
    should_validate_input,
    {
        "valid": "process_context",
        "invalid": "stream_invalid_response",
    },
)

graph_builder.add_conditional_edges(
    "multi_dataset_agent",
    should_visualize,
    {
        "visualization_agent": "visualization_agent",
        END: END,
    },
)

graph_builder.add_conditional_edges(
    "single_dataset_agent",
    should_visualize,
    {
        "visualization_agent": "visualization_agent",
        END: END,
    },
)

graph_builder.add_edge(START, "validate_input")
graph_builder.add_edge("process_context", "check_visualization")
graph_builder.add_edge("check_visualization", "supervisor")
graph_builder.add_edge("stream_invalid_response", END)
graph_builder.add_edge("visualization_agent", END)

agent_graph = graph_builder.compile()
