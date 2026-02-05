from typing import TypedDict

from app.models.schema import DatasetSchema


class SqlQuery(TypedDict):
    query: str
    description: str


class InputState(TypedDict, total=False):
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    user_query: str


class OutputState(TypedDict):
    sql_queries: list[SqlQuery]
    message: str | None


class State(TypedDict, total=False):
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    user_query: str
    semantic_search_results: list[DatasetSchema]
    sql_queries: list[SqlQuery]
    message: str | None
