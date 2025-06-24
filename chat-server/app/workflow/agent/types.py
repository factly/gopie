from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.workflow.graph.visualize_with_code_graph.types import Dataset


class AgentInput(TypedDict):
    messages: list
    dataset_ids: list[str] | None
    project_ids: list[str] | None


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    user_query: str | None
    datasets: list[Dataset] | None
