from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]
    dataset_ids: list[str] | None
    project_ids: list[str] | None
    user_query: str | None
    query_result: dict | None
    viz_data: list[dict] | None
