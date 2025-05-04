from typing import Any, TypedDict


class AnalysisInfo(TypedDict):
    title: str
    date_start: str
    date_end: str


class ColumnSchema(TypedDict):
    name: str
    description: str
    type: str
    sample_values: Any
    non_null_count: int | None


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
    columns_details: list[ColumnSchema]
    columns: list[str]

    alerts: list[str] | None
    duplicates: Any | None
    correlations: Any | None
    missing_values: Any | None
