from typing import Annotated, List, Optional, TypedDict

from app.models.query import (
    QueryResult,
)
from langgraph.graph.message import add_messages


class State(TypedDict):
    dataset_ids: Optional[List[str]]
    project_ids: Optional[List[str]]
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
