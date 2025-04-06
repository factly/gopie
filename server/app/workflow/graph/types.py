from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages

from server.app.models.query import (
    QueryResult,
)


class State(TypedDict):
    dataset_id: Optional[str]
    datasets: list[str]
    subqueries: list[str]
    subquery_index: int
    dataset_info: dict
    query_type: str
    sql_query: str
    retry_count: int
    user_query: str
    messages: Annotated[list, add_messages]
    query_result: QueryResult
