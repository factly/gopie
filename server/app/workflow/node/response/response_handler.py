from app.models.message import ErrorMessage
from app.workflow.graph.types import State

MAX_RETRIES = 3


def route_response_handler(state: State) -> str:
    """Route to the appropriate response handler based on the state"""
    retry_count = state.get("retry_count", 0)
    message = state["messages"][-1]

    subqueries = state.get("subqueries", [])
    query_index = state.get("subquery_index", 0)

    if isinstance(message, ErrorMessage):
        if retry_count >= MAX_RETRIES:
            return "max_iterations_reached"

    if len(subqueries) - 1 > query_index:
        return "next_sub_query"

    return "generate_result"
