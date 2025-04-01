from typing import List

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.callbacks.manager import adispatch_custom_event

from server.app.models.types import AgentEvent, EventData, EventNode, EventStatus


def create_progress_message(event_node: EventNode) -> str:
    """Create a user-friendly progress message based on the event type."""
    event_messages = {
        EventNode.GENERATE_SUBQUERIES: "Breaking down your query into manageable parts...",
        EventNode.IDENTIFY_DATASETS: "Identifying relevant datasets...",
        EventNode.ANALYZE_QUERY: "Analyzing your query...",
        EventNode.ANALYZE_DATASET: "Analyzing dataset structure...",
        EventNode.PLAN_QUERY: "Planning the database query...",
        EventNode.EXECUTE_QUERY: "Executing the query...",
        EventNode.GENERATE_RESULT: "Generating results...",
        EventNode.MAX_ITERATIONS_REACHED: "Max iterations reached. Stopping...",
        EventNode.ERROR: "An error occurred",
        EventNode.TOOL_START: "Starting operation...",
        EventNode.TOOL_END: "Completed operation",
        EventNode.TOOL_ERROR: "Error in operation",
        EventNode.TOOLS: "Using tools...",
    }

    return event_messages.get(event_node, "Processing...")


class AgentEventDispatcher(BaseCallbackHandler):
    """Custom event dispatcher for the Dataful Agent."""

    def __init__(self):
        super().__init__()
        self.events: List[AgentEvent] = []

    async def dispatch_event(
        self, event_node: EventNode, status: EventStatus, data: EventData
    ) -> None:
        """Dispatch a custom event."""
        await adispatch_custom_event(
            "dataful_agent",
            {
                "event_node": event_node.value,
                "status": status.value,
                "message": create_progress_message(event_node),
                "event_data": data.model_dump(),
            },
        )
        self.events.append(
            AgentEvent(
                event_node=event_node,
                status=status,
                message=create_progress_message(event_node),
                data=data,
            )
        )

    def get_events(self) -> List[AgentEvent]:
        """Get all recorded events."""
        return self.events

    def clear_events(self) -> None:
        """Clear all recorded events."""
        self.events = []
