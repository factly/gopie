from app.workflow.graph.multi_dataset_graph.types import State


def route_response_handler(state: State) -> str:
    """
    Route to the appropriate response handler based on the state
    """

    subqueries = state.get("subqueries", [])
    query_index = state.get("subquery_index", 0)

    query_result = state.get("query_result", None)
    current_subquery = query_result.subqueries[query_index]

    has_large_results = False

    for sql_query_info in current_subquery.sql_queries:
        if sql_query_info.contains_large_results:
            has_large_results = True

    if has_large_results:
        return "large_sql_output"

    if len(subqueries) - 1 > query_index:
        return "stream_updates"
    else:
        return "generate_result"
