from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypedDict


@dataclass
class SubQueryInfo:
    """
    A class to represent information about a subquery
    """

    query_text: str
    sql_query_used: str
    sql_query_explanation: str | None = None
    tables_used: str | None = None
    query_type: str | None = None
    error_message: list[dict] | None = None
    retry_count: int = 0
    query_result: Any = None
    tool_used_result: Any = None
    contains_large_results: bool = False
    summary: dict | None = None

    def add_error_message(self, error_message: str, error_origin_type: str):
        if self.error_message is None:
            self.error_message = []
        self.error_message.append({error_origin_type: error_message})

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_text": self.query_text,
            "sql_query_used": self.sql_query_used,
            "sql_query_explanation": self.sql_query_explanation,
            "tables_used": self.tables_used,
            "query_type": self.query_type,
            "query_result": self.query_result,
            "tool_used_result": self.tool_used_result,
            "contains_large_results": self.contains_large_results,
            "summary": self.summary,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }


class QueryInfo(TypedDict, total=False):
    tables_used: str | None
    query_type: str | None
    query_result: Any
    tool_used_result: Any


@dataclass
class QueryResult:
    """
    Aggregates the result of user query with the subqueries executed to
    generate the result.
    """

    original_user_query: str
    execution_time: float
    timestamp: datetime
    subqueries: list[SubQueryInfo] = field(default_factory=list)

    def __post_init__(self):
        if not hasattr(self, "timestamp"):
            self.timestamp = datetime.now()

    def add_subquery(
        self,
        query_text: str,
        sql_query_used: str,
        query_info: QueryInfo | None = None,
    ):
        """
        Add a subquery with detailed information
        """
        subquery_info = SubQueryInfo(
            query_text=query_text,
            sql_query_used=sql_query_used,
            tables_used=query_info.get("tables_used") if query_info else None,
            query_type=query_info.get("query_type") if query_info else None,
            query_result=(
                query_info.get("query_result") if query_info else None
            ),
            tool_used_result=(
                query_info.get("tool_used_result") if query_info else None
            ),
        )
        self.subqueries.append(subquery_info)

    def has_subqueries(self) -> bool:
        """Check if there are any subqueries."""
        return len(self.subqueries) > 0

    def add_error_message(self, error_message: str, error_origin_type: str):
        """
        Add an error message to the current subquery
        """
        self.subqueries[-1].add_error_message(error_message, error_origin_type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_user_query": self.original_user_query,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
            "subqueries": [sq.to_dict() for sq in self.subqueries],
        }

    def calculate_execution_time(self):
        if not hasattr(self, "timestamp"):
            self.timestamp = datetime.now()
        self.execution_time = (datetime.now() - self.timestamp).total_seconds()
