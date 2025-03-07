from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langchain_core.messages import AIMessage
from langgraph.graph.message import add_messages

from src.utils.result_handler import add_result

class State(TypedDict):
    datasets: list[str]
    subqueries: list[str]
    subquery_index: int
    dataset_info: dict
    query_type: str
    sql_query: str
    retry_count: int
    user_query: str
    query_result: Annotated[list[dict], add_result]
    tool_results: List[Dict[str, Any]]
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