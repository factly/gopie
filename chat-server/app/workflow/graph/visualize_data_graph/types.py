from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_query: str | None
    visualization_data: list[dict] | None
    visualization_type: str | None
    visualization_reason: str | None
    formatted_data_for_visualization: dict | None


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
    chat_history: list[BaseMessage]
    user: str
