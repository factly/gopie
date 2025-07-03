from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.workflow.graph.visualize_data_graph.types import Dataset


class AgentInput(TypedDict):
    messages: list
    dataset_ids: list[str] | None
    project_ids: list[str] | None


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    user_query: str | None
    need_semantic_search: bool | None
    required_dataset_ids: list[str] | None
    needs_visualization: bool | None
    visualization_data: list[dict] | None
    datasets: list[Dataset] | None
