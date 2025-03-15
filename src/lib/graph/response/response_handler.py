from src.lib.graph.types import ErrorMessage, State


def route_response_handler(state: State) -> str:
    """Route to the appropriate response handler based on the state"""
    retry_count = state.get("retry_count", 0)
    message = state["messages"][-1]

    subqueries = state.get("subqueries", [])
    query_index = state.get("subquery_index", 0)

    if isinstance(message, ErrorMessage):
        if retry_count >= 3:
            return "max_iterations_reached"

    if len(subqueries) - 1 > query_index:
        return "next_sub_query"

    return "generate_result"
