from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.models.query import SqlQueryInfo
from app.workflow.graph.multi_dataset_graph.types import DatasetsInfo
from app.workflow.graph.single_dataset_graph.types import SingleDatasetInfo


class InputState(TypedDict):
    user_query: str
    multi_datasets_info: DatasetsInfo | None
    single_dataset_info: SingleDatasetInfo | None
    retry_count: int
    validation_result: str | None
    prev_sql_queries: list[str] | None


class OutputState(TypedDict):
    sql_queries: list[SqlQueryInfo] | None
    non_sql_response: str | None
    limitations: str | None
    tables_used: list[str] | None


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_query: str
    sql_queries: list[SqlQueryInfo] | None
    non_sql_response: str | None
    limitations: str | None
    tables_used: list[str] | None
    retry_count: int
    multi_datasets_info: DatasetsInfo | None
    single_dataset_info: SingleDatasetInfo | None
    prev_sql_queries: list[str] | None
    validation_result: str | None
    duckdb_docs_context: str | None
