from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AgentNode(Enum):
    GENERATE_SUBQUERIES = "generate_subqueries"
    IDENTIFY_DATASETS = "identify_datasets"
    PLAN_QUERY = "plan_query"
    EXECUTE_QUERY = "execute_query"
    GENERATE_RESULT = "generate_result"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
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


class ChatTextChunk(BaseModel):
    role: str
    content: str
    type: ChunkType


class ToolMessage(ChatTextChunk):
    category: str


class EventChunkData(BaseModel):
    role: Literal["ai", "system"] | None
    graph_node: AgentNode
    content: str | None
    type: ChunkType
    category: str | None
    datasets_used: list[str] | None = None
    generate_sql_query: str | None = None


class StructuredChatStreamChunk(BaseModel):
    chat_id: str | None = None
    trace_id: str | None = None
    message: ChatTextChunk | ToolMessage | None = None
    datasets_used: list[str] | None = None
    generate_sql_query: str | None = None
    error: Error | None = None

    model_config = ConfigDict(coerce_numbers_to_str=True, extra="forbid")
