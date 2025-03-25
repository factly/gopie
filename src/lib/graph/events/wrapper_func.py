from src.lib.graph.events.dispatcher import AgentEventDispatcher, EventNode, EventStatus, EventData
from src.lib.graph.types import State

event_dispatcher = AgentEventDispatcher()
def create_event_wrapper(name: str, func):
    """Create an event-wrapped async function for graph nodes."""
    async def wrapped_func(state: State):
        try:
            if name == "tools":
                event_dispatcher.dispatch_event(
                    event_node=EventNode.TOOL_START,
                    status=EventStatus.STARTED,
                    data=EventData(
                        input=str(state.get('messages', [])[-1].content),
                    )
                )
            else:
                event_dispatcher.dispatch_event(
                    event_node=EventNode[name.upper()],
                    status=EventStatus.STARTED,
                    data=EventData(
                        input=str(state.get('messages', [])[-1].content),
                    )
                )

            result = await func(state)

            if name == "tools":
                index = state.get('subquery_index')
                result_content = state.get('query_result').subqueries[index].tool_used_result
                event_node = EventNode.TOOL_END
                event_data = EventData(
                    result=str(result_content),
                )
            else:
                result_content = (
                    result.get('messages', [])[-1].content
                    if isinstance(result, dict) and result.get('messages')
                    else str(result)
                )
                event_node = EventNode[name.upper()]
                event_data = EventData(
                    result=result_content,
                )

            event_dispatcher.dispatch_event(event_node, EventStatus.COMPLETED, event_data)
            return result

        except Exception as e:
            error_type = EventNode.TOOL_ERROR if name == "tools" else EventNode.ERROR
            error_data = EventData(
                error=str(e),
            )
            event_dispatcher.dispatch_event(error_type, EventStatus.ERROR, error_data)
            raise

    return wrapped_func