from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage
from pydantic import BaseModel


@dataclass
class SubQueryInfo:
    """
    A class to represent information about a subquery
    """

    query_text: str
    sql_query_used: str
    sql_query_explanation: Optional[str] = None
    tables_used: Optional[str] = None
    query_type: Optional[str] = None
    query_result: Any = None
    tool_used_result: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_text": self.query_text,
            "sql_query_used": self.sql_query_used,
            "sql_query_explanation": self.sql_query_explanation,
            "tables_used": self.tables_used,
            "query_type": self.query_type,
            "query_result": self.query_result,
            "tool_used_result": self.tool_used_result,
        }


@dataclass
class QueryResult:
    """
    A class to represent the result of a query execution along with its metadata
    """

    original_user_query: str
    execution_time: float
    timestamp: datetime
    error_message: Optional[list[dict]] = None
    subqueries: List[SubQueryInfo] = field(default_factory=list)

    def __post_init__(self):
        if not hasattr(self, "timestamp"):
            self.timestamp = datetime.now()

    def has_error(self) -> bool:
        return self.error_message is not None and len(self.error_message) > 0

    def add_subquery(
        self,
        query_text: str,
        sql_query_used: str,
        tables_used: Optional[str] = None,
        query_type: Optional[str] = None,
        query_result: Any = None,
        tool_used_result: Any = None,
    ):
        """
        Add a subquery with detailed information
        """
        subquery_info = SubQueryInfo(
            query_text=query_text,
            sql_query_used=sql_query_used,
            tables_used=tables_used,
            query_type=query_type,
            query_result=query_result,
            tool_used_result=tool_used_result,
        )
        self.subqueries.append(subquery_info)

    def has_subqueries(self) -> bool:
        """Check if there are any subqueries."""
        return len(self.subqueries) > 0

    def add_error_message(self, error_message: str, error_origin_type: str):
        """
        Add an error message to the query result
        """
        if self.error_message is None:
            self.error_message = []
        self.error_message.append({error_origin_type: error_message})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_user_query": self.original_user_query,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
            "subqueries": [sq.to_dict() for sq in self.subqueries],
        }


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


class ColumnSchema(TypedDict):
    """Schema information for a dataset column"""

    name: str
    description: str
    type: str
    sample_values: List[Any]
    non_null_count: Optional[int]
    constraints: Optional[Dict[str, Any]]


class DatasetSchema(TypedDict):
    """Comprehensive schema information for a dataset"""

    name: str
    file_path: str
    file_size_mb: float
    row_count: int
    column_count: int
    columns: List[ColumnSchema]


class EventNode(Enum):
    GENERATE_SUBQUERIES = "generate_subqueries"
    IDENTIFY_DATASETS = "identify_datasets"
    ANALYZE_QUERY = "analyze_query"
    ANALYZE_DATASET = "analyze_dataset"
    PLAN_QUERY = "plan_query"
    EXECUTE_QUERY = "execute_query"
    GENERATE_RESULT = "generate_result"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    ERROR = "error"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"
    TOOLS = "tools"


class EventStatus(Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ERROR = "error"


class EventData(BaseModel):
    """Data structure for event data."""

    input: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AgentEvent:
    """Event data structure for agent events."""

    event_node: EventNode
    status: EventStatus
    message: str
    data: EventData