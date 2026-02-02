from langgraph.graph import END, START, StateGraph

from .node.execute_sql import execute_sql
from .node.prepare_data import prepare_data
from .node.routing import route_after_sql_generation
from .node.sql_agent import sql_agent
from .node.validate_result import route_result_validation, validate_result
from .types import ConfigSchema, InputState, OutputState, State

graph_builder = StateGraph(
    state_schema=State,
    config_schema=ConfigSchema,
    input_schema=InputState,
    output_schema=OutputState,
)

graph_builder.add_node("prepare_data", prepare_data)
graph_builder.add_node("sql_agent", sql_agent)
graph_builder.add_node("execute_sql", execute_sql)
graph_builder.add_node("validate_result", validate_result)

graph_builder.add_conditional_edges(
    "sql_agent",
    route_after_sql_generation,
    {
        "no_sql_queries": "validate_result",
        "execute_sql": "execute_sql",
    },
)

graph_builder.add_conditional_edges(
    "validate_result",
    route_result_validation,
    {
        "pass_on_results": END,
        "rerun_query": "sql_agent",
    },
)

graph_builder.add_edge(START, "prepare_data")
graph_builder.add_edge("prepare_data", "sql_agent")
graph_builder.add_edge("execute_sql", "validate_result")


single_dataset_graph = graph_builder.compile()
