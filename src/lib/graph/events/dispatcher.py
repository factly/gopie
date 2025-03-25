from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.callbacks.manager import adispatch_custom_event
from pydantic import BaseModel


class EventNode(Enum):
    GENERATE_SUBQUERIES = "generate_subqueries"
    IDENTIFY_DATASETS = "identify_datasets"
    ANALYZE_QUERY = "analyze_query"
    ANALYZE_DATASET = "analyze_dataset"
    PLAN_QUERY = "plan_query"
    EXECUTE_QUERY = "execute_query"
    GENERATE_RESULT = "generate_result"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    ERROR = "error"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"
    TOOLS = "tools"


class EventData(BaseModel):
    """Data structure for event data."""

    input: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None


class EventStatus(Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentEvent:
    """Event data structure for agent events."""

    event_node: EventNode
    status: EventStatus
    message: str
    data: EventData


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
