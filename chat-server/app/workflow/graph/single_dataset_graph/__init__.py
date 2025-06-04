from langgraph.graph import END, START, StateGraph

from app.workflow.graph.multi_dataset_graph.types import ConfigSchema
from app.workflow.graph.single_dataset_graph.node.process_query import (
    process_query,
)
from app.workflow.graph.single_dataset_graph.node.response import response
from app.workflow.graph.single_dataset_graph.types import State

graph_builder = StateGraph(State, config_schema=ConfigSchema)

graph_builder.add_node("process_query", process_query)
graph_builder.add_node("response", response)

graph_builder.add_edge(START, "process_query")
graph_builder.add_edge("process_query", "response")
graph_builder.add_edge("response", END)

simple_graph = graph_builder.compile()
