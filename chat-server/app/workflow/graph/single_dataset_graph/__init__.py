from langgraph.graph import END, START, StateGraph

from app.workflow.graph.multi_dataset_graph.types import ConfigSchema
from app.workflow.graph.single_dataset_graph.node.check_visualization import (
    check_visualization,
    route_next_node,
)
from app.workflow.graph.single_dataset_graph.node.process_query import (
    process_query,
    should_retry,
)
from app.workflow.graph.single_dataset_graph.node.response import response
from app.workflow.graph.single_dataset_graph.node.transfer_visual_call import (
    transfer_visual_call,
)
from app.workflow.graph.single_dataset_graph.types import State

graph_builder = StateGraph(State, config_schema=ConfigSchema)

graph_builder.add_node("process_query", process_query)
graph_builder.add_node("check_visualization", check_visualization)
graph_builder.add_node("handoff_to_visualizer", transfer_visual_call)
graph_builder.add_node("response", response)

graph_builder.add_conditional_edges(
    "process_query",
    should_retry,
    {
        "retry": "process_query",
        "check_visualization": "check_visualization",
    },
)

graph_builder.add_conditional_edges(
    "check_visualization",
    route_next_node,
    {
        "handoff_to_visualizer_agent": "handoff_to_visualizer",
        "response": "response",
    },
)

graph_builder.add_edge(START, "process_query")
graph_builder.add_edge("handoff_to_visualizer", END)
graph_builder.add_edge("response", END)

single_dataset_graph = graph_builder.compile()
