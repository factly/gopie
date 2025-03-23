from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class AgentEventType(Enum):
    SUBQUERY_GENERATION = "subquery_generation"
    DATASET_IDENTIFICATION = "dataset_identification"
    QUERY_ANALYSIS = "query_analysis"
    DATASET_ANALYSIS = "dataset_analysis"
    QUERY_PLANNING = "query_planning"
    QUERY_EXECUTION = "query_execution"
    RESULT_GENERATION = "result_generation"
    ERROR = "error"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"


@dataclass
class AgentEvent:
    event_type: AgentEventType
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class AgentEventDispatcher(BaseCallbackHandler):
    """Custom event dispatcher for the Dataful Agent."""

    def __init__(self):
        super().__init__()
        self.events: List[AgentEvent] = []

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Handle LLM start events."""
        self.events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_START,
                data={"tool": "LLM", "prompts": prompts},
                metadata=kwargs,
            )
        )

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Handle LLM end events."""
        self.events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_END,
                data={"tool": "LLM", "response": response.generations},
                metadata=kwargs,
            )
        )

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Handle LLM error events."""
        self.events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_ERROR,
                data={"tool": "LLM", "error": str(error)},
                metadata=kwargs,
            )
        )

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Handle tool start events."""
        self.events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_START,
                data={"tool": serialized.get("name", "unknown"), "input": input_str},
                metadata=kwargs,
            )
        )

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Handle tool end events."""
        self.events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_END,
                data={"output": output},
                metadata=kwargs,
            )
        )

    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Handle tool error events."""
        self.events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_ERROR,
                data={"error": str(error)},
                metadata=kwargs,
            )
        )

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        """Handle chain start events."""
        chain_type = serialized.get("name", "unknown")
        self.events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_START,
                data={"chain": chain_type, "inputs": inputs},
                metadata=kwargs,
            )
        )

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Handle chain end events."""
        self.events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_END,
                data={"outputs": outputs},
                metadata=kwargs,
            )
        )

    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """Handle chain error events."""
        self.events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_ERROR,
                data={"error": str(error)},
                metadata=kwargs,
            )
        )

    def dispatch_event(self, event_type: AgentEventType, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Dispatch a custom event."""
        self.events.append(AgentEvent(event_type=event_type, data=data, metadata=metadata))

    def get_events(self) -> List[AgentEvent]:
        """Get all recorded events."""
        return self.events

    def clear_events(self) -> None:
        """Clear all recorded events."""
        self.events = []