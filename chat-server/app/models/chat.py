from enum import Enum
from typing import TypedDict

from pydantic import BaseModel, ConfigDict


class Role(str, Enum):
    AI = "ai"
    SYSTEM = "system"
    INTERMEDIATE = "intermediate"


class NodeConfig(BaseModel):
    streams_ai_content: bool = False
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


class ChunkType(Enum):
    START = "start"
    END = "end"
    BODY = "body"
    STREAM = "stream"


class Error(BaseModel):
    type: str
    message: str


class ChatTextChunk(BaseModel):
    role: Role
    content: str
    type: ChunkType


class ToolMessage(ChatTextChunk):
    category: str


class EventChunkData(BaseModel):
    role: Role | None
    graph_node: str
    content: str | None
    type: ChunkType
    category: str | None
    datasets_used: list[str] | None = None
    generated_sql_query: list[str] | None = None


class StructuredChatStreamChunk(BaseModel):
    chat_id: str | None = None
    trace_id: str | None = None
    message: ChatTextChunk | ToolMessage | None = None
    datasets_used: list[str] | None = None
    generated_sql_query: list[str] | None = None
    error: Error | None = None
    finish_reason: str | None = None

    model_config = ConfigDict(coerce_numbers_to_str=True, extra="forbid")


# OpenAI Compatibility
class OpenAiStreamingState(TypedDict):
    completion_id: str
    created: int
    model: str | None
    tool_messages: list
    datasets_used: list
    content_so_far: str
    chunk_count: int
    tool_call_id: int
    last_sent_tool_messages: list
    last_sent_datasets: list
    last_sent_sql_query: list[str]
    yield_content: bool
    delta_content: str
    finish_reason: str
