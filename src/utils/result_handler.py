from typing import TypeVar, Callable, Any, cast

def add_result(messages: list[dict], addition: list[dict]) -> list[dict]:
    """Adds new query results to the existing results list.

    Args:
        messages: The existing list of query results
        addition: New query results to add

    Returns:
        Updated list containing both existing and new results
    """
    if not messages:
        messages = []
    if isinstance(addition, list):
        messages.extend(addition)
    else:
        messages.append(addition)
    return messages

# Type variable and function overload for type safety
T = TypeVar("T")

def add_result_partial(addition: list[dict]) -> Callable[[list[dict]], list[dict]]:
    """Creates a partial function that adds specific results.

    Args:
        addition: The results to add

    Returns:
        Function that takes and returns a list of results
    """
    def add_result_fn(x: list[dict]) -> list[dict]:
        return add_result(x, addition)
    return add_result_fn