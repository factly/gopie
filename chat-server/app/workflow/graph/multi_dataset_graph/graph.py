from langgraph.graph import END, START, StateGraph

from app.tool_utils.tool_node import ModifiedToolNode as ToolNode
from app.tool_utils.tools import ToolNames

from .node.analyze_dataset import analyze_dataset
from .node.analyze_query import analyze_query, route_from_analysis
from .node.execute_query import execute_query
from .node.generate_subqueries import generate_subqueries
from .node.identify_datasets import identify_datasets, route_from_datasets
from .node.plan_query import plan_query
from .node.response_handler import route_response_handler
from .node.stream_updates import (
    check_further_execution_requirement,
    stream_updates,
)
from .node.validate_result import route_result_validation, validate_result
from .types import ConfigSchema, InputState, OutputState, State

graph_builder = StateGraph(
    state_schema=State,
    config_schema=ConfigSchema,
    input_schema=InputState,
    output_schema=OutputState,
)

graph_builder.add_node("generate_subqueries", generate_subqueries)
graph_builder.add_node("identify_datasets", identify_datasets)
graph_builder.add_node("analyze_query", analyze_query)
graph_builder.add_node("plan_query", plan_query)
graph_builder.add_node("execute_query", execute_query)
graph_builder.add_node("analyze_dataset", analyze_dataset)
graph_builder.add_node("stream_updates", stream_updates)
graph_builder.add_node("validate_result", validate_result)
graph_builder.add_node("tools", ToolNode(tool_names=list(ToolNames)))
graph_builder.add_node("route_response", lambda state: state)
graph_builder.add_node("pass_on_results", lambda state: state)

graph_builder.add_conditional_edges(
    "analyze_query",
    route_from_analysis,
    {
        "identify_datasets": "identify_datasets",
        "basic_conversation": "route_response",
        "tools": "tools",
    },
)

graph_builder.add_conditional_edges(
    "identify_datasets",
    route_from_datasets,
    {
        "analyze_dataset": "analyze_dataset",
        "no_datasets_found": "route_response",
    },
)

graph_builder.add_conditional_edges(
    "validate_result",
    route_result_validation,
    {
        "route_response": "route_response",
        "replan": "plan_query",
        "reidentify_datasets": "identify_datasets",
    },
)

graph_builder.add_conditional_edges(
    "route_response",
    route_response_handler,
    {
        "pass_on_results": "pass_on_results",
        "stream_updates": "stream_updates",
    },
)

graph_builder.add_conditional_edges(
    "stream_updates",
    check_further_execution_requirement,
    {
        "end_execution": END,
        "next_sub_query": "analyze_query",
    },
)

graph_builder.add_edge(START, "generate_subqueries")
graph_builder.add_edge("generate_subqueries", "analyze_query")
graph_builder.add_edge("analyze_dataset", "plan_query")
graph_builder.add_edge("tools", "analyze_query")
graph_builder.add_edge("plan_query", "execute_query")
graph_builder.add_edge("execute_query", "validate_result")
graph_builder.add_edge("pass_on_results", END)

multi_dataset_graph = graph_builder.compile()
