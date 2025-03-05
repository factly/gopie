from typing import Any, Dict, Callable, TypeVar, cast
import inspect
import functools

# Type variable for function return type
T = TypeVar('T')

def append_tool_result(state: Dict[str, Any], tool_name: str, result: Any) -> None:
    """
    Appends a tool's result to the state's tool_results key

    Args:
        state: The current state dictionary
        tool_name: The name of the tool that was called
        result: The result returned by the tool
    """
    if 'tool_results' not in state:
        state['tool_results'] = []

    # Create a record of the tool call with its result
    tool_result = {
        'tool': tool_name,
        'result': result
    }

    # Append to the tool_results list
    state['tool_results'].append(tool_result)

def with_result_capture(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that captures the result of a tool call and adds it to the state

    Args:
        func: The tool function to wrap

    Returns:
        A wrapped function that captures and stores its result in the state
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Execute the original function
        result = func(*args, **kwargs)

        # Check if state is provided in the arguments
        state = None
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        # Find state parameter in args or kwargs
        for i, arg in enumerate(args):
            if i < len(param_names) and param_names[i] == 'state':
                state = arg
                break

        if state is None and 'state' in kwargs:
            state = kwargs['state']

        # If we found a state, append the result to it
        if state is not None:
            tool_name = getattr(func, '__name__', str(func))
            append_tool_result(state, tool_name, result)

        return result

    return wrapper