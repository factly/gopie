from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.models.query import QueryResult


class State(TypedDict):
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    datasets: list[str]
    subqueries: list[str]
    subquery_index: int
    datasets_info: dict
    user_query: str
    messages: Annotated[list, add_messages]
    query_result: QueryResult
    tool_call_count: int
    trace_id: str
