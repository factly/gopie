from langgraph.graph import END, START, StateGraph

from app.workflow.graph.multi_dataset_graph.types import ConfigSchema
from app.workflow.graph.single_dataset_graph.node.process_query import (
    process_query,
)
from app.workflow.graph.single_dataset_graph.node.response import response
from app.workflow.graph.single_dataset_graph.node.supervisor import (
    route_supervisor,
    supervisor,
)
from app.workflow.graph.single_dataset_graph.node.visualization_adapter import (
    visualization_adapter,
)
from app.workflow.graph.single_dataset_graph.types import State

graph_builder = StateGraph(State, config_schema=ConfigSchema)

graph_builder.add_node("process_query", process_query)
graph_builder.add_node("supervisor", supervisor)
graph_builder.add_node("response", response)
graph_builder.add_node("visualizer_agent", visualization_adapter)

graph_builder.add_edge(START, "process_query")
graph_builder.add_edge("process_query", "supervisor")

graph_builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "response": "response",
        "visualizer_agent": "visualizer_agent",
    },
)

graph_builder.add_edge("response", END)
graph_builder.add_edge("visualizer_agent", END)

simple_graph = graph_builder.compile()
