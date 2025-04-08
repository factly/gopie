from typing import Any, List, Optional, TypedDict


class AnalysisInfo(TypedDict):
    """Information about the analysis"""

    title: str
    date_start: str
    date_end: str


class ColumnSchema(TypedDict):
    """Schema information for a dataset column"""

    name: str
    description: str
    type: str
    sample_values: Any
    non_null_count: Optional[int]


class DatasetSchema(TypedDict):
    """Comprehensive schema information for a dataset"""

    name: str
    description: str
    dataset_id: str
    file_path: str
    project_id: str
    analysis: AnalysisInfo
    row_count: int
    col_count: int
    columns_details: List[ColumnSchema]
    columns: List[str]

    alerts: Optional[List[str]]
    duplicates: Optional[Any]
    correlations: Optional[Any]
    missing_values: Optional[Any]
