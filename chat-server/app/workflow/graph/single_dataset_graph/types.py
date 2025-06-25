from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class InputState(TypedDict):
    messages: list[BaseMessage]
    dataset_id: str | None
    user_query: str


class OutputState(TypedDict):
    query_result: dict | None
    response_text: str


class State(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int
    dataset_id: str | None
    user_query: str | None
    query_result: dict | None
    response_text: str
    error: str | None
    failed_queries: list[dict] | None
