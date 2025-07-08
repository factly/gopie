from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.models.query import QueryResult
from app.models.schema import DatasetSchema


# TODO: Type these fields correctly.
class DatasetsInfo(TypedDict):
    schemas: List[DatasetSchema]
    column_assumptions: Optional[List]
    correct_column_requirements: Optional[List]


class InputState(TypedDict):
    dataset_ids: List[str] | None
    project_ids: List[str] | None
    messages: List[BaseMessage]
    user_query: str
    need_semantic_search: bool | None
    required_dataset_ids: List[str] | None


class OutputState(TypedDict):
    query_result: QueryResult
    response_text: str


class State(TypedDict):
    dataset_ids: List[str] | None
    project_ids: List[str] | None
    identified_datasets: List[str]
    subqueries: List[str]
    subquery_index: int
    datasets_info: DatasetsInfo
    user_query: str
    messages: Annotated[List[BaseMessage], add_messages]
    query_result: QueryResult
    response_text: str
    tool_call_count: int
    need_semantic_search: bool | None
    required_dataset_ids: List[str] | None


class ConfigSchema(TypedDict):
    model_id: str
    trace_id: str
    chat_history: List[BaseMessage]
    user: str
