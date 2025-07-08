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


class ExtraData(BaseModel):
    name: str
    args: Dict[str, Any]


class EventChunkData(BaseModel):
    role: Role | None
    content: str
    category: str | None
    extra_data: ExtraData | None = None
