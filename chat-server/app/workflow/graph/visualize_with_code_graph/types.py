from typing import Annotated, Any, List, Optional, Sequence, TypedDict

from e2b_code_interpreter import AsyncSandbox
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class Dataset(BaseModel):
    data: List[List[Any]]
    description: str
    csv_path: Optional[str] = None


class ResultPaths(BaseModel):
    """Use this to return the paths to the json files created by the agent."""

    visualization_result_paths: List[str]


class InputState(TypedDict):
    user_query: str
    datasets: List[Dataset]


class OutputState(TypedDict):
    s3_paths: List[str]


class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    datasets: List[Dataset]
    sandbox: AsyncSandbox | None = None
    user_query: str
    is_input_prepared: bool = False
    s3_paths: List[str] = []
