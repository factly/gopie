from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.models.query import QueryResult


class InputState(TypedDict):
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    messages: list[BaseMessage]
    user_query: str


class OutputState(TypedDict):
    query_result: QueryResult
    response_text: str


class State(TypedDict):
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    identified_datasets: list[str]
    subqueries: list[str]
    subquery_index: int
    datasets_info: dict
    user_query: str
    messages: Annotated[list, add_messages]
    query_result: QueryResult
    response_text: str
    tool_call_count: int


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
    chat_history: list[BaseMessage]
    user: str
