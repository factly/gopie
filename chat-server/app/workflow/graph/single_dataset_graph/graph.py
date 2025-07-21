from langgraph.graph import END, START, StateGraph

from .node.process_query import process_query
from .node.validate_result import route_result_validation, validate_result
from .types import ConfigSchema, InputState, OutputState, State

graph_builder = StateGraph(
    state_schema=State,
    config_schema=ConfigSchema,
    input_schema=InputState,
    output_schema=OutputState,
)

graph_builder.add_node("process_query", process_query)
graph_builder.add_node("validate_result", validate_result)

graph_builder.add_conditional_edges(
    "validate_result",
    route_result_validation,
    {
        "pass_on_results": END,
        "rerun_query": "process_query",
    },
)

graph_builder.add_edge(START, "process_query")
graph_builder.add_edge("process_query", "validate_result")
graph_builder.add_edge("validate_result", END)

single_dataset_graph = graph_builder.compile()
