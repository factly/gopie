from langgraph.graph import END, START, StateGraph

from app.tools import TOOLS
from app.tools.tool_node import ToolNode
from app.workflow.events.dispatcher import AgentEventDispatcher
from app.workflow.events.wrapper_func import create_event_wrapper
from app.workflow.graph.types import State
from app.workflow.node.analyze_dataset import analyze_dataset
from app.workflow.node.analyze_query import analyze_query, route_from_analysis
from app.workflow.node.execute_query import execute_query, route_query_replan
from app.workflow.node.generate_subqueries import generate_subqueries
from app.workflow.node.identify_datasets import identify_datasets
from app.workflow.node.plan_query import plan_query
from app.workflow.node.response.generate_result import generate_result
from app.workflow.node.response.max_iterations import max_iterations_reached
from app.workflow.node.response.response_handler import route_response_handler

graph_builder = StateGraph(State)
event_dispatcher = AgentEventDispatcher()

GRAPH_NODES = {
    "generate_subqueries": generate_subqueries,
    "identify_datasets": identify_datasets,
    "analyze_query": analyze_query,
    "plan_query": plan_query,
    "execute_query": execute_query,
    "generate_result": generate_result,
    "max_iterations_reached": max_iterations_reached,
    "analyze_dataset": analyze_dataset,
}

for name, func in GRAPH_NODES.items():
    graph_builder.add_node(name, create_event_wrapper(name, func))

graph_builder.add_node(
    "tools",
    ToolNode(tools=list(TOOLS.values()), event_dispatcher=event_dispatcher),
)
graph_builder.add_node("response_router", lambda x: x)

graph_builder.add_conditional_edges(
    "analyze_query",
    route_from_analysis,
    {
        "identify_datasets": "identify_datasets",
        "basic_conversation": "response_router",
        "tools": "tools",
    },
)

graph_builder.add_conditional_edges(
    "execute_query",
    route_query_replan,
    {
        "response_router": "response_router",
        "replan": "plan_query",
        "reidentify_datasets": "identify_datasets",
    },
)

graph_builder.add_conditional_edges(
    "response_router",
    route_response_handler,
    {
        "next_sub_query": "analyze_query",
        "generate_result": "generate_result",
        "max_iterations_reached": "max_iterations_reached",
    },
)

graph_builder.add_edge(START, "generate_subqueries")
graph_builder.add_edge("generate_subqueries", "analyze_query")
graph_builder.add_edge("analyze_dataset", "plan_query")
graph_builder.add_edge("tools", "analyze_query")
graph_builder.add_edge("identify_datasets", "analyze_dataset")
graph_builder.add_edge("plan_query", "execute_query")
graph_builder.add_edge("generate_result", END)
graph_builder.add_edge("max_iterations_reached", END)

graph = graph_builder.compile()
