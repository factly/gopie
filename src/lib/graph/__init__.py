from langgraph.graph import END, START, StateGraph
from typing import AsyncGenerator

from src.lib.graph.analyze_dataset import analyze_dataset
from src.lib.graph.analyze_query import analyze_query, route_from_analysis
from src.lib.graph.events.dispatcher import AgentEventDispatcher, AgentEventType
from src.lib.graph.events.stream_handler import create_progress_message
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
import json

event_dispatcher = AgentEventDispatcher()
graph_builder = StateGraph(State)

def create_event_wrapper(name: str, func):
    """Create an event-wrapped async function for graph nodes."""
    async def wrapped_func(state: State):
        try:
            if name == "tools":
                event_dispatcher.dispatch_event(
                    AgentEventType.TOOL_START,
                    {
                        "tool": "tools",
                        "input": str(state.get('messages', [])[-1].content),
                        "status": "started"
                    }
                )
            else:
                event_dispatcher.dispatch_event(
                    AgentEventType[name.upper()],
                    {"status": "started", "node": name}
                )

            result = await func(state)

            if name == "tools":
                index = state.get('subquery_index')
                result_content = state.get('query_result').subqueries[index].tool_used_result
                event_type = AgentEventType.TOOL_END
                event_data = {
                    "tool": "tools",
                    "output": str(result_content),
                    "status": "completed"
                }
            else:
                result_content = (
                    result.get('messages', [])[-1].content
                    if isinstance(result, dict) and result.get('messages')
                    else str(result)
                )
                event_type = AgentEventType[name.upper()]
                event_data = {"status": "completed", "result": result_content}

            event_dispatcher.dispatch_event(event_type, event_data)
            return result

        except Exception as e:
            error_type = AgentEventType.TOOL_ERROR if name == "tools" else AgentEventType.ERROR
            error_data = (
                {"tool": "tools", "error": str(e)}
                if name == "tools"
                else {"error": str(e), "node": name}
            )
            event_dispatcher.dispatch_event(error_type, error_data)
            raise

    return wrapped_func

GRAPH_NODES = {
    "generate_subqueries": generate_subqueries,
    "identify_datasets": identify_datasets,
    "analyze_query": analyze_query,
    "plan_query": plan_query,
    "execute_query": execute_query,
    "generate_result": generate_result,
    "max_iterations_reached": max_iterations_reached,
    "analyze_dataset": analyze_dataset,
    "tools": ToolNode(tools=list(TOOLS.values()))
}

for name, func in GRAPH_NODES.items():
    graph_builder.add_node(name, create_event_wrapper(name, func))

graph_builder.add_node("response_router", lambda x: x)

graph_builder.add_conditional_edges(
    "analyze_query",
    route_from_analysis,
    {
        "identify_datasets": "identify_datasets",
        "basic_conversation": "response_router",
        "tools": "tools",
    }
)

graph_builder.add_conditional_edges(
    "execute_query",
    route_query_replan,
    {
        "response_router": "response_router",
        "replan": "plan_query",
        "reidentify_datasets": "identify_datasets",
    }
)

graph_builder.add_conditional_edges(
    "response_router",
    route_response_handler,
    {
        "next_sub_query": "analyze_query",
        "generate_result": "generate_result",
        "max_iterations_reached": "max_iterations_reached",
    }
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
        str: JSON-formatted event data for streaming
    """
    event_dispatcher.clear_events()
    input_state = {"messages": [{"role": "user", "content": user_input}]}

    try:
        async for event in graph.astream(input_state):
            for agent_event in event_dispatcher.get_events():
                yield json.dumps({
                    "type": agent_event.event_type.value,
                    "message": create_progress_message(agent_event),
                    "data": agent_event.data
                }) + "\n"

            event_dispatcher.clear_events()

            if isinstance(event, dict):
                for key, value in event.items():
                    if isinstance(value, dict) and "messages" in value:
                        yield json.dumps({
                            "type": "message",
                            "message": str(value["messages"][-1].content),
                            "data": {"node": key}
                        }) + "\n"

    except Exception as e:
        yield json.dumps({
            "type": "error",
            "message": f"Error during streaming: {str(e)}",
            "data": {"error": str(e)}
        }) + "\n"

def visualize_graph():
    try:
        with open("graph/graph.png", "wb") as f:
            f.write(graph.get_graph().draw_mermaid_png())
    except Exception as e:
        raise e
