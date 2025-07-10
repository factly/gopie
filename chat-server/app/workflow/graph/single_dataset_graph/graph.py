from langgraph.graph import END, START, StateGraph

from .node.process_query import process_query
from .node.response import response
from .node.validate_result import route_result_validation, validate_result
from .types import ConfigSchema, InputState, OutputState, State

graph_builder = StateGraph(
    State, config_schema=ConfigSchema, input=InputState, output=OutputState
)

graph_builder.add_node("process_query", process_query)
graph_builder.add_node("response", response)
graph_builder.add_node("validate_result", validate_result)

graph_builder.add_conditional_edges(
    "validate_result",
    route_result_validation,
    {
        "respond_to_user": "response",
        "rerun_query": "process_query",
    },
)

graph_builder.add_edge(START, "process_query")
graph_builder.add_edge("process_query", "validate_result")
graph_builder.add_edge("response", END)

single_dataset_graph = graph_builder.compile()
