from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.models.data import ColumnValueMatching
from app.models.query import QueryResult
from app.models.schema import DatasetSchema
from app.workflow.types import ColumnAssumptions


class SingleDatasetInfo(TypedDict):
    dataset_schema: DatasetSchema
    sample_data_csv: str
    column_assumptions: list[ColumnAssumptions] | None
    correct_column_requirements: ColumnValueMatching | None


class InputState(TypedDict):
    messages: list[BaseMessage]
    dataset_id: str | None
    user_query: str
    prev_sql_queries: list | None


class OutputState(TypedDict):
    query_result: QueryResult


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    dataset_id: str | None
    user_query: str | None
    query_result: QueryResult
    dataset_info: SingleDatasetInfo
    prev_sql_queries: list | None
    validation_result: str | None
    recommendation: str
    sql_queries: list[str] | None
    explanations: list[str] | None


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
    chat_history: list[BaseMessage]
    user: str
