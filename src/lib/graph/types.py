from typing import Annotated, TypedDict, Union, Dict, List, Any
from langchain_core.messages import AIMessage
from langgraph.graph.message import add_messages

class State(TypedDict):
    datasets: list[str]
    dataset_metadata: dict
    conversational: bool
    query: str
    retry_count: int
    user_query: str
    query_result: dict
    messages: Annotated[list, add_messages]

class IntermediateStep(AIMessage):
    """Represents an intermediate step in the processing pipeline"""
    type: str = "intermediate_step"

    @classmethod
    def from_text(cls, text: str) -> "IntermediateStep":
        return cls(content=text)

class ErrorMessage(AIMessage):
    """Represents an error message"""
    type: str = "error_message"

    @classmethod
    def from_text(cls, text: str) -> "ErrorMessage":
        return cls(content=text)