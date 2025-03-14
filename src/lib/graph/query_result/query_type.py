from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SubQueryInfo:
    """
    A class to represent information about a subquery
    """

    query_text: str
    sql_query_used: str
    tables_used: Optional[str] = None
    query_type: Optional[str] = None
    query_result: Any = None
    tool_used_result: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_text": self.query_text,
            "sql_query_used": self.sql_query_used,
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
