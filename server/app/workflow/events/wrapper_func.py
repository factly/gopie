from app.models.event import EventData, EventNode, EventStatus
from app.workflow.events.dispatcher import AgentEventDispatcher
from app.workflow.graph.types import State

event_dispatcher = AgentEventDispatcher()


def create_event_wrapper(name: str, func):
    async def wrapped_func(state: State):
        try:
            await event_dispatcher.dispatch_event(
                event_node=EventNode[name.upper()],
                status=EventStatus.STARTED,
                data=EventData(
                    input=parse_data(state.get("messages", [])[-1].content)
                ),
            )

            result = await func(state)

            event_data = EventData(
                result=parse_data(result.get("messages", [])[-1].content),
            )

            await event_dispatcher.dispatch_event(
                event_node=EventNode[name.upper()],
                status=EventStatus.COMPLETED,
                data=event_data,
            )

            return result

        except Exception as e:
            error_data = EventData(
                error=str(e),
            )
            await event_dispatcher.dispatch_event(
                event_node=EventNode[name.upper()],
                status=EventStatus.ERROR,
                data=error_data,
            )
            raise

    return wrapped_func


def parse_data(data: list | str) -> dict | str:
    if isinstance(data, list):
        return data[0]
    return data
