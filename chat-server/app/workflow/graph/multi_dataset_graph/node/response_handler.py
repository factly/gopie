from app.workflow.graph.multi_dataset_graph.types import State


def route_response_handler(state: State) -> str:
    """
    Determines the next response action based on the current subquery index in the state.
    
    Returns:
        str: "stream_updates" if there are more subqueries to process, otherwise "pass_on_results".
    """

    subqueries = state.get("subqueries", [])
    query_index = state.get("subquery_index", 0)

    if len(subqueries) - 1 > query_index:
        return "stream_updates"
    else:
        return "pass_on_results"
