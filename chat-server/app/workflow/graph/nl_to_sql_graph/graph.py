from langgraph.graph import END, START, StateGraph

from .node.semantic_search import semantic_search
from .node.sql_agent import sql_agent
from .node.supervisor import supervisor
from .types import InputState, OutputState, State

graph_builder = StateGraph(
    state_schema=State,
    input_schema=InputState,
    output_schema=OutputState,
)

graph_builder.add_node(
    supervisor,
    destinations=("sql_agent", "semantic_search"),
)
graph_builder.add_node("sql_agent", sql_agent)
graph_builder.add_node("semantic_search", semantic_search)

graph_builder.add_edge(START, "supervisor")
graph_builder.add_edge("semantic_search", "sql_agent")
graph_builder.add_edge("sql_agent", END)

nl_to_sql_graph = graph_builder.compile()
