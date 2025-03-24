from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

class AgentEventType(Enum):
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


@dataclass
class AgentEvent:
    """Event data structure for agent events."""
    event_type: AgentEventType
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class AgentEventDispatcher(BaseCallbackHandler):
    """Custom event dispatcher for the Dataful Agent."""

    def __init__(self):
        super().__init__()
        self.events: List[AgentEvent] = []

    def dispatch_event(self, event_type: AgentEventType, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Dispatch a custom event."""
        self.events.append(AgentEvent(event_type=event_type, data=data, metadata=metadata))

    def get_events(self) -> List[AgentEvent]:
        """Get all recorded events."""
        return self.events

    def clear_events(self) -> None:
        """Clear all recorded events."""
        self.events = []