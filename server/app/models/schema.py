from typing import Any, Dict, List, Optional, TypedDict


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
