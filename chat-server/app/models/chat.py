from enum import Enum

from pydantic import BaseModel, ConfigDict


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


class ChunkType(Enum):
    START = "start"
    END = "end"
    BODY = "body"
    STREAM = "stream"


class Error(BaseModel):
    type: str
    message: str


class Role(Enum):
    AI = "ai"
    SYSTEM = "system"
    INTERMEDIATE = "intermediate"


class ChatTextChunk(BaseModel):
    role: Role
    content: str
    type: ChunkType


class ToolMessage(ChatTextChunk):
    category: str


class EventChunkData(BaseModel):
    role: Role | None
    graph_node: AgentNode
    content: str | None
    type: ChunkType
    category: str | None
    datasets_used: list[str] | None = None
    generated_sql_query: str | None = None


class StructuredChatStreamChunk(BaseModel):
    chat_id: str | None = None
    trace_id: str | None = None
    message: ChatTextChunk | ToolMessage | None = None
    datasets_used: list[str] | None = None
    generated_sql_query: str | None = None
    error: Error | None = None
    finish_reason: str | None = None

    model_config = ConfigDict(coerce_numbers_to_str=True, extra="forbid")
