from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]
    retry_count: int
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    user_query: str | None
    query_result: dict | None
    wants_visualization: bool | None
    raw_sql_queries_data: list[dict] | None
    error: str | None
    failed_queries: list[dict] | None
