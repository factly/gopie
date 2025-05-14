from app.workflow.graph.types import State


def route_response_handler(state: State) -> str:
    """
    Route to the appropriate response handler based on the state
    """

    subqueries = state.get("subqueries", [])
    query_index = state.get("subquery_index", 0)

    query_result = state.get("query_result", None)
    current_subquery = query_result.subqueries[query_index]

    if (
        current_subquery.contains_large_results
        and not current_subquery.summary
    ):
        return "large_sql_output"

    if len(subqueries) - 1 > query_index:
        return "stream_updates"
    else:
        return "generate_result"
