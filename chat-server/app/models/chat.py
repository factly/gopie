from enum import Enum
from typing import Any

from pydantic import BaseModel


class Role(str, Enum):
    AI = "ai"
    SYSTEM = "system"
    INTERMEDIATE = "intermediate"


class NodeEventConfig(BaseModel):
    role: Role = Role.INTERMEDIATE
    progress_message: str = "Processing..."


class ExtraData(BaseModel):
    name: str
    args: dict[str, Any]


class EventChunkData(BaseModel):
    role: Role | None
    content: str
    category: str | None
    extra_data: ExtraData | None = None
