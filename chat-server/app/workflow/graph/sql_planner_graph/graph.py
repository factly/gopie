from langgraph.graph import END, START, StateGraph

from app.models.schema import ConfigSchema

from .generate_sql import generate_sql
from .search_docs import search_duckdb_docs
from .types import InputState, OutputState, State

workflow = StateGraph(
    state_schema=State,
    config_schema=ConfigSchema,
    input_schema=InputState,
    output_schema=OutputState,
)

workflow.add_node("generate_sql", generate_sql)
workflow.add_node("search_duckdb_docs", search_duckdb_docs)

# workflow.add_conditional_edges(
#     START,
#     should_search_duckdb_docs,
#     {
#         "search_docs": "search_duckdb_docs",
#         "generate_sql": "generate_sql",
#     },
# )


# workflow.add_edge("search_duckdb_docs", "generate_sql")
workflow.add_edge(START, "generate_sql")
workflow.add_edge("generate_sql", END)

sql_planning_agent = workflow.compile()
