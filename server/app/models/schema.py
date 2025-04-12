from typing import Any, List, Optional, TypedDict


class AnalysisInfo(TypedDict):
    title: str
    date_start: str
    date_end: str


class ColumnSchema(TypedDict):
    name: str
    description: str
    type: str
    sample_values: Any
    non_null_count: Optional[int]


class DatasetSchema(TypedDict):
    name: str  # User friendly name for the dataset
    dataset_name: str  # Name that should be used in sql queries
    dataset_description: str
    project_id: str
    dataset_id: str
    file_path: str
    analysis: AnalysisInfo
    row_count: int
    col_count: int
    columns_details: List[ColumnSchema]
    columns: List[str]

    alerts: Optional[List[str]]
    duplicates: Optional[Any]
    correlations: Optional[Any]
    missing_values: Optional[Any]
