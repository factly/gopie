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
    data: list[bytes]
    errors: list[str] = []


class InputState(TypedDict):
    user_query: str
    datasets: list[Dataset] | None
    previous_visualization_result_paths: list[str] | None
    relevant_sql_queries: list[str] | None


class OutputState(TypedDict):
    s3_paths: list[str]


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    previous_visualization_result_paths: list[str] | None
    datasets: list[Dataset] | None
    user_query: str
    result: VisualizationResult
    sandbox: AsyncSandbox | None
    is_input_prepared: bool
    s3_paths: list[str]
    tool_call_count: int
    feedback_count: int
    executed_python_code: str | None
    relevant_sql_queries: list[str] | None
    result_images_b64: list[str]
