from typing import Annotated, Any, Sequence, TypedDict

from e2b_code_interpreter import AsyncSandbox
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class Dataset(BaseModel):
    data: list[list[Any]]
    description: str
    csv_path: str | None = None


class ResultPaths(BaseModel):
    """
    Use this to return the paths to the json files created by the agent,\
    after visualization
    """

    visualization_result_paths: list[str]


class InputState(TypedDict):
    user_query: str
    datasets: list[Dataset]


class OutputState(TypedDict):
    s3_paths: list[str]


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    datasets: list[Dataset]
    user_query: str
    sandbox: AsyncSandbox | None
    is_input_prepared: bool
    s3_paths: list[str]
