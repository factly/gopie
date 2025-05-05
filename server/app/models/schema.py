from typing import Any, TypedDict


class AnalysisInfo(TypedDict):
    title: str
    date_start: str
    date_end: str


class ColumnSchema(TypedDict):
    column_name: str
    column_type: str
    min: int
    max: int
    approx_unique: int
    avg: float
    std: float
    q25: float
    q50: float
    q75: float
    count: int
    sample_values: list[Any]
    null_percentage: float


class DatasetSchema(TypedDict):
    name: str  # User friendly name for the dataset
    dataset_name: str  # Name that should be used in sql queries
    dataset_description: str
    project_id: str
    dataset_id: str
    file_path: str
    columns: list[ColumnSchema]
