from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.models.query import QueryResult


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
    tool_call_count: int


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
