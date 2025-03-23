from langgraph.graph import END, START, StateGraph

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
from typing import AsyncGenerator, Dict, Any

# Initialize event dispatcher
event_dispatcher = AgentEventDispatcher()

graph_builder = StateGraph(State)

# Add nodes with event dispatching
def add_node_with_events(name, func):
    async def wrapped_func(state: State):
        event_dispatcher.dispatch_event(
            AgentEventType[name.upper()],
            {"status": "started", "state": state}
        )
        try:
            result = await func(state)
            event_dispatcher.dispatch_event(
                AgentEventType[name.upper()],
                {"status": "completed", "result": result}
            )
            return result
        except Exception as e:
            event_dispatcher.dispatch_event(
                AgentEventType.ERROR,
                {"error": str(e), "node": name}
            )
            raise

    graph_builder.add_node(name, wrapped_func)

add_node_with_events("generate_subqueries", generate_subqueries)
add_node_with_events("identify_datasets", identify_datasets)
add_node_with_events("analyze_query", analyze_query)
add_node_with_events("plan_query", plan_query)
add_node_with_events("execute_query", execute_query)
add_node_with_events("generate_result", generate_result)
add_node_with_events("max_iterations_reached", max_iterations_reached)
add_node_with_events("analyze_dataset", analyze_dataset)

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
    """Stream graph updates for user input with event tracking."""
    event_dispatcher.clear_events()

    input_state = {"messages": [{"role": "user", "content": user_input}]}

    try:
        for event in graph.stream(input_state):
            current_events = event_dispatcher.get_events()

            for agent_event in current_events:
                formatted_event = {
                    "type": agent_event.event_type.value,
                    "message": create_progress_message(agent_event),
                    "data": agent_event.data
                }
                yield json.dumps(formatted_event) + "\n"

            event_dispatcher.clear_events()

            if isinstance(event, dict):
                for key in event:
                    if isinstance(event[key], dict) and "messages" in event[key]:
                        message_event = {
                            "type": "message",
                            "message": str(event[key]["messages"][-1].content),
                            "data": {"node": key}
                        }
                        yield json.dumps(message_event) + "\n"

    except Exception as e:
        error_event = {
            "type": "error",
            "message": f"Error during streaming: {str(e)}",
            "data": {"error": str(e)}
        }
        yield json.dumps(error_event) + "\n"

def visualize_graph():
    try:
        with open("graph/graph.png", "wb") as f:
            f.write(graph.get_graph().draw_mermaid_png())
    except Exception as e:
        raise e
