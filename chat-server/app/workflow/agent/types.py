from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

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
    need_semantic_search: bool | None
    required_dataset_ids: list[str] | None
    needs_visualization: bool | None
    datasets: list[Dataset] | None
    invalid_input: bool | None
