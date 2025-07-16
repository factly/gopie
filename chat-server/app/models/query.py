from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypedDict


@dataclass
class SqlQueryInfo:
    sql_query: str
    explanation: str
    sql_query_result: list | None = None
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sql_query": self.sql_query,
            "explanation": self.explanation,
            "sql_query_result": self.sql_query_result,
            "success": self.success,
            "error": self.error,
        }


class ToolUsedResult(TypedDict):
    tool_call_id: str
    content: str
    name: str | None


@dataclass
class SubQueryInfo:
    """
    A class to represent information about a subquery
    """

    query_text: str
    sql_queries: list[SqlQueryInfo]
    tables_used: str | None = None
    query_type: str | None = None
    error_message: list[dict] | None = None
    retry_count: int = 0
    tool_used_result: list[ToolUsedResult] | None = None
    confidence_score: int = 5
    node_messages: dict = field(default_factory=dict)

    def add_error_message(self, error_message: str, error_origin_type: str):
        if self.error_message is None:
            self.error_message = []
        self.error_message.append({error_origin_type: error_message})

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_text": self.query_text,
            "sql_queries": [query.to_dict() for query in self.sql_queries],
            "tables_used": self.tables_used,
            "query_type": self.query_type,
            "tool_used_result": self.tool_used_result,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "confidence_score": self.confidence_score,
            "node_messages": self.node_messages,
        }


@dataclass
class SingleDatasetQueryResult:
    user_query: str
    user_friendly_dataset_name: str | None
    dataset_name: str | None
    sql_results: list[SqlQueryInfo] | None
    response_for_non_sql: str | None
    error: list[dict] | None


class QueryInfo(TypedDict, total=False):
    tables_used: str | None
    query_type: str | None
    tool_used_result: list[ToolUsedResult] | None
    confidence_score: int
    node_messages: dict


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
        sql_queries: list[SqlQueryInfo],
        query_info: QueryInfo | None = None,
    ):
        subquery_info = SubQueryInfo(
            query_text=query_text,
            sql_queries=sql_queries,
            tables_used=query_info.get("tables_used") if query_info else None,
            query_type=query_info.get("query_type") if query_info else None,
            tool_used_result=(query_info.get("tool_used_result") if query_info else None),
            confidence_score=(query_info.get("confidence_score", 5) if query_info else 5),
            node_messages=(query_info.get("node_messages", {}) if query_info else {}),
        )
        self.subqueries.append(subquery_info)

    def has_subqueries(self) -> bool:
        return len(self.subqueries) > 0

    def add_error_message(self, error_message: str, error_origin_type: str):
        self.subqueries[-1].add_error_message(error_message, error_origin_type)

    def set_node_message(self, node_name: str, node_message: Any):
        if self.has_subqueries():
            self.subqueries[-1].node_messages[node_name] = node_message

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
