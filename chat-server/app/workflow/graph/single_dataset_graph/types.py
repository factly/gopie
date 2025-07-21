from typing import Annotated, TypedDict

from app.models.query import QueryResult, ValidationResult
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class InputState(TypedDict):
    messages: list[BaseMessage]
    dataset_id: str | None
    user_query: str


class OutputState(TypedDict):
    query_result: QueryResult


class State(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int
    validation_result: ValidationResult | None
    dataset_id: str | None
    user_query: str | None
    query_result: QueryResult


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
    chat_history: list[BaseMessage]
    user: str
