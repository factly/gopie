from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.models.data import ColumnValueMatching
from app.models.query import SqlQueryInfo
from app.models.schema import DatasetSchema
from app.workflow.graph.single_dataset_graph.types import SingleDatasetInfo
from app.workflow.types import ColumnAssumptions


class DatasetsInfo(TypedDict):
    schemas: list[DatasetSchema]
    column_assumptions: list[ColumnAssumptions] | None
    correct_column_requirements: ColumnValueMatching | None


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
    multi_datasets_info: DatasetsInfo | None
    single_dataset_info: SingleDatasetInfo | None


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
    match_columns_retry_count: int
