import json
from typing import AsyncGenerator, Dict

from src.lib.graph.events.dispatcher import AgentEvent, AgentEventType


def format_event(event: AgentEvent) -> Dict:
    """Format an event for streaming to the user."""
    formatted = {
        "type": event.event_type.value,
        "data": event.data
    }

    if event.metadata:
        formatted["metadata"] = event.metadata

    return formatted


async def stream_events(events: AsyncGenerator[AgentEvent, None]) -> AsyncGenerator[str, None]:
    """Stream formatted events to the user."""
    async for event in events:
        formatted_event = format_event(event)
        yield json.dumps(formatted_event) + "\n"


def create_progress_message(event: AgentEvent) -> str:
    """Create a user-friendly progress message based on the event type."""
    event_messages = {
        AgentEventType.GENERATE_SUBQUERIES: "Breaking down your query into manageable parts...",
        AgentEventType.IDENTIFY_DATASETS: "Identifying relevant datasets...",
        AgentEventType.ANALYZE_QUERY: "Analyzing your query...",
        AgentEventType.ANALYZE_DATASET: "Analyzing dataset structure...",
        AgentEventType.PLAN_QUERY: "Planning the database query...",
        AgentEventType.EXECUTE_QUERY: "Executing the query...",
        AgentEventType.GENERATE_RESULT: "Generating results...",
        AgentEventType.MAX_ITERATIONS_REACHED: "Max iterations reached. Stopping...",
        AgentEventType.ERROR: f"Error: {event.data.get('error', 'An unknown error occurred')}",
        AgentEventType.TOOL_START: f"Starting {event.data.get('tool', 'operation')}...",
        AgentEventType.TOOL_END: f"Completed {event.data.get('tool', 'operation')}",
        AgentEventType.TOOL_ERROR: f"Error in {event.data.get('tool', 'operation')}: {event.data.get('error', 'An unknown error occurred')}"
    }

    return event_messages.get(event.event_type, "Processing...")