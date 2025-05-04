from dataclasses import dataclass
from enum import Enum

from openai import BaseModel


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


class EventStatus(Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ERROR = "error"


class EventData(BaseModel):
    input: str | None = None
    result: str | None = None
    error: str | None = None


@dataclass
class AgentEvent:
    event_node: EventNode
    status: EventStatus
    message: str
    data: EventData
