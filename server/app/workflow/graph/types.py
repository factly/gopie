from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from server.app.models.types import (
    ColumnSchema,
    DatasetSchema,
    ErrorMessage,
    IntermediateStep,
    QueryResult,
)


class State(TypedDict):
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

# The class definitions for IntermediateStep, ErrorMessage, ColumnSchema, and DatasetSchema
# have been moved to server.app.models.types
