from typing import Annotated, TypedDict

from app.models.query import QueryResult
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class InputState(TypedDict):
    messages: list[BaseMessage]
    dataset_id: str | None
    user_query: str
    previous_sql_queries: list | None


class OutputState(TypedDict):
    query_result: QueryResult


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    retry_count: int
    dataset_id: str | None
    user_query: str | None
    query_result: QueryResult
    previous_sql_queries: list | None
    recommendation: str


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
    chat_history: list[BaseMessage]
    user: str
