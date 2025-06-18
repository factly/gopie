from langgraph.types import Command

from app.workflow.graph.single_dataset_graph.types import State


async def transfer_visual_call(state: State) -> Command:
    user_query = state.get("user_query", "")
    query_result = state.get("query_result") or {}

    raw_sql_queries_data = []
    sql_queries = query_result.get("sql_queries", [])

    for result in sql_queries:
        if result.get("result") and result.get("success", True):
            raw_sql_queries_data.extend(result["result"])

    input_state = {
        "messages": state["messages"],
        "user_query": user_query,
        "viz_data": raw_sql_queries_data,
        "query_result": query_result,
    }

    return Command(
        goto="visualizer_agent",
        graph=Command.PARENT,
        update=input_state,
    )
