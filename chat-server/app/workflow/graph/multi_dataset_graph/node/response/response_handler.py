from app.workflow.graph.multi_dataset_graph.types import State


def route_response_handler(state: State) -> str:
    """
    Route to the appropriate response handler based on the state
    """

    subqueries = state.get("subqueries", [])
    query_index = state.get("subquery_index", 0)

    if len(subqueries) - 1 > query_index:
        return "stream_updates"
    else:
        return "pass_on_results"
