from langgraph.graph import END, START, StateGraph
from src.lib.graph.execute_query import execute_query, route_query_replan
from src.lib.graph.plan_query import plan_query
from src.lib.graph.response.generate_result import generate_result
from src.lib.graph.response.max_iterations import max_iterations_reached
from src.lib.graph.response.no_result import no_results_handler
from src.lib.graph.response.response_handler import route_response_handler
from src.lib.graph.types import State
from src.lib.graph.identify_datasets import identify_datasets, is_conversational_input
from src.lib.graph.analyze_dataset import analyze_dataset
from src.lib.graph.analyze_query import analyze_query, route_from_analysis
from src.tools import TOOLS
from src.tools.tool_node import ToolNode

graph_builder = StateGraph(State)
graph_builder.add_node("identify_datasets", identify_datasets)
graph_builder.add_node("analyze_query", analyze_query)
graph_builder.add_node("plan_query", plan_query)
graph_builder.add_node("execute_query", execute_query)
graph_builder.add_node("generate_result", generate_result)
graph_builder.add_node("max_iterations_reached", max_iterations_reached)
graph_builder.add_node("no_results_handler", no_results_handler)
graph_builder.add_node("analyze_dataset", analyze_dataset)
graph_builder.add_node("tools", ToolNode(tools=list(TOOLS.values())))
graph_builder.add_node("response_router", lambda x: x)

graph_builder.add_conditional_edges(
    "execute_query",
    route_query_replan,
    {
        "response_router": "response_router",
        "replan": "plan_query",
        "reidentify_datasets": "identify_datasets"
    },
)

graph_builder.add_conditional_edges(
    "analyze_query",
    route_from_analysis,
    {
        "identify_datasets": "identify_datasets",
        "basic_conversation": "generate_result",
        "tools": "tools"
    },
)

graph_builder.add_conditional_edges(
    "response_router",
    route_response_handler,
    {
        "generate_result": "generate_result",
        "max_iterations_reached": "max_iterations_reached",
        "no_results": "no_results_handler"
    },
)

graph_builder.add_edge("tools", "analyze_query")
graph_builder.add_edge(START, "analyze_query")
graph_builder.add_edge("identify_datasets", "analyze_dataset")
graph_builder.add_edge("analyze_dataset", "plan_query")
graph_builder.add_edge("plan_query", "execute_query")
graph_builder.add_edge("generate_result", END)
graph_builder.add_edge("max_iterations_reached", END)
graph_builder.add_edge("no_results_handler", END)

graph = graph_builder.compile()

async def stream_graph_updates(user_input: str):
    """Stream graph updates for user input."""
    event_types = [
        "generate subqueries",
        "identify_datasets",
        "analyze_query",
        "analyze_dataset",
        "plan_query",
        "execute_query",
        "generate_result",
        "max_iterations_reached",
        "no_results_handler"
    ]

    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for event_type in event_types:
            if event_type in event:
                if event[event_type] and "messages" in event[event_type]:
                    yield str(event[event_type]["messages"][-1].content) + "\n\n"

def visualize_graph():
    try:
        with open("graph/graph.png", "wb") as f:
            f.write(graph.get_graph().draw_mermaid_png())
    except Exception as e:
            raise e
