from typing import Any, TypedDict


class AnalysisInfo(TypedDict):
    title: str
    date_start: str
    date_end: str


class ColumnSchema(TypedDict):
    column_name: str
    column_description: str
    column_type: str
    min: Any
    max: Any
    approx_unique: int
    avg: Any
    std: Any
    q25: Any
    q50: Any
    q75: Any
    count: int
    sample_values: list[Any]
    null_percentage: dict


class DatasetSchema(TypedDict):
    name: str  # User friendly name for the dataset
    dataset_name: str  # Name that should be used in sql queries
    dataset_description: str
    project_id: str
    dataset_id: str
    columns: list[ColumnSchema]
