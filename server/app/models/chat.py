from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class AgentNode(Enum):
    GENERATE_SUBQUERIES = "generate_subqueries"
    IDENTIFY_DATASETS = "identify_datasets"
    PLAN_QUERY = "plan_query"
    EXECUTE_QUERY = "execute_query"
    GENERATE_RESULT = "generate_result"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    TOOL = "tool"


class ToolCategory(Enum):
    LIST_DATASETS = "list_datasets"


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
    category: Any


class StructuredChatStreamChunk(BaseModel):
    chat_id: str | None = None
    trace_id: str | None = None
    message: ChatTextChunk | ToolMessage | None = None
    datasets_used: list[str] | None = None
    generate_sql_query: str | None = None
    error: Error | None = None

    model_config = ConfigDict(coerce_numbers_to_str=True, extra="forbid")
