from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel


class Role(str, Enum):
    AI = "ai"
    SYSTEM = "system"
    INTERMEDIATE = "intermediate"


class NodeConfig(BaseModel):
    role: Role = Role.INTERMEDIATE
    progress_message: str = "Processing..."


# This nodes are used to streaming purposes
class AgentNode(Enum):
    GENERATE_SUBQUERIES = "generate_subqueries"
    IDENTIFY_DATASETS = "identify_datasets"
    ANALYZE_DATASETS = "analyze_datasets"
    PLAN_QUERY = "plan_query"
    GENERATE_RESULT = "generate_result"
    STREAM_UPDATES = "stream_updates"
    TOOLS = "tools"
    UNKNOWN = "unknown"

    PROCESS_QUERY = "process_query"
    RESPONSE = "response"


class ExtraData(BaseModel):
    name: str
    args: Dict[str, Any]


class EventChunkData(BaseModel):
    role: Role | None
    content: str
    category: str | None
    extra_data: ExtraData | None = None
