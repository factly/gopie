import json
from typing import AsyncGenerator

from langgraph.graph import END, START, StateGraph

from src.lib.graph.analyze_dataset import analyze_dataset
from src.lib.graph.analyze_query import analyze_query, route_from_analysis
from src.lib.graph.events.wrapper_func import create_event_wrapper, event_dispatcher
from src.lib.graph.execute_query import execute_query, route_query_replan
from src.lib.graph.generate_subqueries import generate_subqueries
from src.lib.graph.identify_datasets import identify_datasets
from src.lib.graph.plan_query import plan_query
from src.lib.graph.response.generate_result import generate_result
from src.lib.graph.response.max_iterations import max_iterations_reached
from src.lib.graph.response.response_handler import route_response_handler
from src.lib.graph.types import State
from src.tools import TOOLS
from src.tools.tool_node import ToolNode

graph_builder = StateGraph(State)

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

graph_builder.add_node("tools", ToolNode(tools=list(TOOLS.values())))
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


async def stream_graph_updates(user_input: str) -> AsyncGenerator[str, None]:
    """Stream graph updates for user input with event tracking.

    Args:
        user_input (str): The user's input query

    Yields:
        str: JSON-formatted event data for streaming in SSE format
    """
    event_dispatcher.clear_events()
    input_state = {"messages": [{"role": "user", "content": user_input}]}

    try:
        async for event in graph.astream_events(input_state, version="v2"):
            if event.get("event", None) == "on_custom_event":
                formatted_event = event.get("data", {})
                yield f"data: {json.dumps(formatted_event)}\n\n"
    except Exception as e:
        yield f"data: {
            json.dumps(
                {
                    'type': 'error',
                    'message': f'Error during streaming: {str(e)}',
                    'data': {'error': str(e)},
                }
            )
        }\n\n"


def visualize_graph():
    try:
        with open("graph/graph.png", "wb") as f:
            f.write(graph.get_graph().draw_mermaid_png())
    except Exception as e:
        raise e
