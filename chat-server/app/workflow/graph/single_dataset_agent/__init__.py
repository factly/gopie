from langgraph.graph import END, START, StateGraph

from app.workflow.graph.single_dataset_agent.node.simple_plan_query import (
    simple_plan_query,
)
from app.workflow.graph.single_dataset_agent.types import ConfigSchema, State

graph_builder = StateGraph(State, config_schema=ConfigSchema)

graph_builder.add_node("simple_plan_query", simple_plan_query)

graph_builder.add_edge(START, "simple_plan_query")
graph_builder.add_edge("simple_plan_query", END)

simple_graph = graph_builder.compile()
