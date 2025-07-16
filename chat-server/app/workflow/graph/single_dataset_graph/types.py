from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SQLQueryResult(TypedDict):
    sql_query: str
    explanation: str
    result: list[dict[str, Any]] | None
    success: bool
    error: str | None


class SingleDatasetQueryResult(TypedDict, total=False):
    user_query: str
    user_friendly_dataset_name: str | None
    dataset_name: str | None
    sql_results: list[SQLQueryResult] | None
    response_for_non_sql: str | None
    timestamp: str
    error: str | None


class InputState(TypedDict):
    messages: list[BaseMessage]
    dataset_id: str | None
    user_query: str


class ValidationResult(TypedDict):
    is_valid: bool
    reasoning: str
    recommendation: str
    confidence: float
    missing_elements: list[str]


class OutputState(TypedDict):
    query_result: SingleDatasetQueryResult | None


class State(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int
    validation_result: ValidationResult | None
    dataset_id: str | None
    user_query: str | None
    query_result: SingleDatasetQueryResult | None


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
    chat_history: list[BaseMessage]
    user: str
