from src.lib.graph.types import ErrorMessage, State

def route_response_handler(state: State) -> str:
    """
    Route to the appropriate response handler based on the state
    """
    retry_count = state.get("retry_count", 0)
    message = state["messages"][-1]
    query_result = state.get("query_result", [])

    if isinstance(message, ErrorMessage) and retry_count >= 3:
        return "max_iterations_reached"

    # Check for no results case
    if not query_result:
        return "no_results"

    # Default to normal result generation
    return "generate_result"