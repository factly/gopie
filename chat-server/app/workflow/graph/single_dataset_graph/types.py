from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SQLQueryResult(TypedDict):
    sql_query: str
    explanation: str
    result: list[dict[str, Any]] | None
    success: bool
    large_result: str | None
    error: str | None


class FailedQuery(TypedDict):
    sql_query: str
    error: str


class SingleDatasetQueryResult(TypedDict, total=False):
    user_query: str
    user_friendly_dataset_name: str | None
    dataset_name: str | None
    sql_queries: list[SQLQueryResult] | None
    response_for_non_sql: str | None
    timestamp: str


class InputState(TypedDict):
    messages: list[BaseMessage]
    dataset_id: str | None
    user_query: str


class OutputState(TypedDict):
    query_result: SingleDatasetQueryResult | None
    response_text: str


class State(TypedDict):
    messages: Annotated[list, add_messages]
    validation_retry_count: int
    validation_result_str: str | None
    dataset_id: str | None
    user_query: str | None
    query_result: SingleDatasetQueryResult | None
    response_text: str
    error: str | None
    failed_queries: list[FailedQuery] | None


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
    chat_history: list[BaseMessage]
    user: str
