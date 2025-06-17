from langgraph.graph import END, START, StateGraph

from app.workflow.graph.visualize_data_graph.node.choose_visualization import (
    choose_visualization,
)
from app.workflow.graph.visualize_data_graph.node.format_data_for_visualization import (
    DataFormatter,
)
from app.workflow.graph.visualize_data_graph.node.response import (
    visualization_response,
)
from app.workflow.graph.visualize_data_graph.types import ConfigSchema, State

data_formatter = DataFormatter()


graph_builder = StateGraph(State, config_schema=ConfigSchema)

graph_builder.add_node("choose_visualization", choose_visualization)
graph_builder.add_node(
    "format_data_for_visualization",
    data_formatter.format_data_for_visualization,
)
graph_builder.add_node("visualization_response", visualization_response)

graph_builder.add_edge(START, "choose_visualization")
graph_builder.add_edge("choose_visualization", "format_data_for_visualization")
graph_builder.add_edge(
    "format_data_for_visualization", "visualization_response"
)
graph_builder.add_edge("visualization_response", END)

visualize_data_graph = graph_builder.compile()
