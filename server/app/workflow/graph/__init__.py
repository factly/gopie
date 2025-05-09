from langgraph.graph import END, START, StateGraph

from app.tools import TOOLS
from app.tools.tool_node import ToolNode
from app.workflow.graph.types import State
from app.workflow.node.analyze_dataset import analyze_dataset
from app.workflow.node.analyze_query import analyze_query, route_from_analysis
from app.workflow.node.execute_query import execute_query, route_query_replan
from app.workflow.node.generate_subqueries import generate_subqueries
from app.workflow.node.identify_datasets import identify_datasets
from app.workflow.node.plan_query import plan_query
from app.workflow.node.response.extract_summary import extract_summary
from app.workflow.node.response.generate_result import generate_result
from app.workflow.node.response.max_iterations import max_iterations_reached
from app.workflow.node.response.response_handler import route_response_handler
from app.workflow.node.validate_query_result import validate_query_result

graph_builder = StateGraph(State)

graph_builder.add_node("generate_subqueries", generate_subqueries)
graph_builder.add_node("identify_datasets", identify_datasets)
graph_builder.add_node("analyze_query", analyze_query)
graph_builder.add_node("plan_query", plan_query)
graph_builder.add_node("execute_query", execute_query)
graph_builder.add_node("generate_result", generate_result)
graph_builder.add_node("max_iterations_reached", max_iterations_reached)
graph_builder.add_node("analyze_dataset", analyze_dataset)
graph_builder.add_node("validate_query_result", validate_query_result)
graph_builder.add_node("extract_summary", extract_summary)
graph_builder.add_node("tools", ToolNode(tools=list(TOOLS.values())))
graph_builder.add_node("route_response", lambda x: x)

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
    "execute_query",
    route_query_replan,
    {
        "validate_query_result": "validate_query_result",
        "replan": "plan_query",
        "reidentify_datasets": "identify_datasets",
    },
)

graph_builder.add_conditional_edges(
    "route_response",
    route_response_handler,
    {
        "next_sub_query": "analyze_query",
        "generate_result": "generate_result",
        "max_iterations_reached": "max_iterations_reached",
        "large_sql_output": "extract_summary",
    },
)

graph_builder.add_edge(START, "generate_subqueries")
graph_builder.add_edge("generate_subqueries", "analyze_query")
graph_builder.add_edge("analyze_dataset", "plan_query")
graph_builder.add_edge("tools", "analyze_query")
graph_builder.add_edge("identify_datasets", "analyze_dataset")
graph_builder.add_edge("plan_query", "execute_query")
graph_builder.add_edge("validate_query_result", "route_response")
graph_builder.add_edge("extract_summary", "route_response")
graph_builder.add_edge("generate_result", END)
graph_builder.add_edge("max_iterations_reached", END)

graph = graph_builder.compile()
