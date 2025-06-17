from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.workflow.graph.visualize_data_graph.node.choose_visualization import (
    choose_visualization,
)
from app.workflow.graph.visualize_data_graph.node.format_data_for_visualization import (
    DataFormatter,
)
from app.workflow.graph.visualize_data_graph.types import ConfigSchema, State

data_formatter = DataFormatter()


graph_builder = StateGraph(State, config_schema=ConfigSchema)

graph_builder.add_node("choose_visualization", choose_visualization)
graph_builder.add_node(
    "format_data_for_visualization",
    data_formatter.format_data_for_visualization,
)

graph_builder.add_edge(START, "choose_visualization")
graph_builder.add_edge("choose_visualization", "format_data_for_visualization")
graph_builder.add_edge("format_data_for_visualization", END)

visualize_data_graph = graph_builder.compile()


async def call_visualize_data_graph(
    input_state: State, config: RunnableConfig
):
    return await visualize_data_graph.ainvoke(input_state, config)
