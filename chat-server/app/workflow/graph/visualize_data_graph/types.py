from typing import Annotated, Any, Sequence, TypedDict

from e2b_code_interpreter import AsyncSandbox
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class Dataset(BaseModel):
    data: list[list[Any]]
    description: str
    csv_path: str | None = None


class VisualizationResult(BaseModel):
    data: list[str]
    errors: list[str] = []

class InputState(TypedDict):
    user_query: str
    datasets: list[Dataset]


class OutputState(TypedDict):
    s3_paths: list[str]


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    datasets: list[Dataset]
    user_query: str
    result: VisualizationResult
    sandbox: AsyncSandbox | None
    is_input_prepared: bool
    s3_paths: list[str]
