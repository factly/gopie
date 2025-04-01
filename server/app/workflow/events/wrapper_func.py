from server.app.models.types import EventData, EventNode, EventStatus
from server.app.workflow.events.dispatcher import AgentEventDispatcher
from server.app.workflow.graph.types import State

event_dispatcher = AgentEventDispatcher()


def create_event_wrapper(name: str, func):
    """Create an event-wrapped async function for graph nodes."""

    async def wrapped_func(state: State):
        try:
            await event_dispatcher.dispatch_event(
                event_node=EventNode[name.upper()],
                status=EventStatus.STARTED,
                data=EventData(
                    input=str(state.get("messages", [])[-1].content),
                ),
            )

            result = await func(state)

            result_content = (
                result.get("messages", [])[-1].content
                if isinstance(result, dict) and result.get("messages")
                else str(result)
            )
            event_data = EventData(
                result=result_content,
            )

            await event_dispatcher.dispatch_event(
                EventNode[name.upper()], EventStatus.COMPLETED, event_data
            )

            return result

        except Exception as e:
            error_data = EventData(
                error=str(e),
            )
            await event_dispatcher.dispatch_event(
                EventNode.ERROR, EventStatus.ERROR, error_data
            )
            raise

    return wrapped_func
