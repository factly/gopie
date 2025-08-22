from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.models.query import QueryResult
from app.workflow.graph.visualize_data_graph.types import Dataset


class AgentInput(TypedDict):
    messages: list
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    initial_user_query: str | None


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    initial_user_query: str | None
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    user_query: str | None
    new_data_needed: bool | None
    generate_visualization: bool | None
    previous_json_paths: list[str] | None
    relevant_datasets_ids: list[str] | None
    relevant_sql_queries: list[str] | None
    datasets: list[Dataset] | None
    invalid_input: bool | None
    query_result: QueryResult | None
    continue_execution: bool | None
