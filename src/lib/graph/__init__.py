from langgraph.graph import END, START, StateGraph
from src.lib.graph.generate_result import generate_result
from src.lib.graph.execute_query import execute_query, route_query_replan
from src.lib.graph.plan_query import plan_query
from src.lib.graph.types import State
from src.lib.graph.identify_datasets import identify_datasets, is_conversational_input
from src.lib.graph.analyze_dataset import analyze_dataset

graph_builder = StateGraph(State)
graph_builder.add_node("identify_datasets", identify_datasets)
graph_builder.add_node("plan_query", plan_query)
graph_builder.add_node("execute_query", execute_query)
graph_builder.add_node("generate_result", generate_result)
graph_builder.add_node("analyze_dataset", analyze_dataset)

graph_builder.add_conditional_edges(
    "execute_query",
    route_query_replan,
    {"generate_result": "generate_result", "replan": "plan_query", "reidentify_datasets": "identify_datasets"},
)
graph_builder.add_conditional_edges(
    "identify_datasets",
    is_conversational_input,
    {"analyze_dataset": "analyze_dataset", "basic_conversation": "generate_result"},
)

graph_builder.add_edge("analyze_dataset", "plan_query")
graph_builder.add_edge("plan_query", "execute_query")
graph_builder.add_edge(START, "identify_datasets")
graph_builder.add_edge("generate_result", END)

graph = graph_builder.compile()

async def stream_graph_updates(user_input: str):
    """Stream graph updates for user input."""
    event_types = ["generate subqueries", "identify_datasets", "analyze_dataset", "plan_query", "execute_query", "generate_result"]

    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for event_type in event_types:
            if event_type in event:
                if "messages" in event[event_type]:
                    yield str(event[event_type]["messages"][-1].content) + "\n\n"

def visualize_graph():
    try:
        with open("graph/graph.png", "wb") as f:
            f.write(graph.get_graph().draw_mermaid_png())
    except Exception as e:
            raise e
