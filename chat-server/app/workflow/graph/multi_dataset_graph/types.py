from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.models.data import ColumnValueMatching
from app.models.query import QueryResult
from app.models.schema import DatasetSchema


class FuzzyValue(TypedDict):
    name: str
    exact_values: list[str]
    fuzzy_values: list[str]


class ColumnAssumptions(TypedDict):
    dataset: str
    columns: list[FuzzyValue]


class DatasetsInfo(TypedDict):
    schemas: list[DatasetSchema]
    column_assumptions: list[ColumnAssumptions] | None
    correct_column_requirements: ColumnValueMatching | None


class InputState(TypedDict):
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    messages: list[BaseMessage]
    user_query: str
    relevant_datasets_ids: list[str] | None
    previous_sql_queries: list[str] | None


class OutputState(TypedDict):
    query_result: QueryResult
    continue_execution: bool | None


class State(TypedDict):
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    identified_datasets: list[str]
    subqueries: list[str]
    subquery_index: int
    datasets_info: DatasetsInfo
    user_query: str
    messages: Annotated[list[BaseMessage], add_messages]
    query_result: QueryResult
    tool_call_count: int
    relevant_datasets_ids: list[str] | None
    previous_sql_queries: list[str] | None
    retry_count: int
    recommendation: str
    continue_execution: bool | None


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
    chat_history: list[BaseMessage]
    user: str


class ValidationResult(TypedDict):
    is_valid: bool
    reasoning: str
    recommendation: str
    confidence: float
    missing_elements: list[str]
