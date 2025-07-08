from typing import Any, List, Optional

from pydantic import BaseModel


class ColumnDetails(BaseModel):
    column_name: str
    column_type: str
    default: Optional[Any] = None
    extra: Optional[Any] = None
    key: Optional[Any] = None
    null: str


class DatasetDetails(BaseModel):
    id: str
    name: str
    alias: str
    description: str
    format: str
    row_count: int
    columns: List[ColumnDetails]
    size: int
    file_path: str
    created_at: str
    updated_at: str
    created_by: str
    updated_by: str
    dataset_custom_prompt: Optional[str] = None
    project_custom_prompt: Optional[str] = None


class ColumnValueMatching(BaseModel):
    class VerifiedValue(BaseModel):
        value: str
        match_type: str = "exact"
        found_in_database: bool

    class SuggestedAlternative(BaseModel):
        requested_value: str
        match_type: str = "fuzzy"
        found_similar_values: bool
        similar_values: List[str] = []

    class ColumnAnalysis(BaseModel):
        column_name: str
        verified_values: List["ColumnValueMatching.VerifiedValue"] = []
        suggested_alternatives: List[
            "ColumnValueMatching.SuggestedAlternative"
        ] = []

    class DatasetAnalysis(BaseModel):
        dataset_name: str
        columns_analyzed: List["ColumnValueMatching.ColumnAnalysis"] = []

    analysis_type: str = "column_value_verification"
    description: str = "Results of verifying column values across datasets"
    datasets: dict[str, "ColumnValueMatching.DatasetAnalysis"] = {}
    summary: str = ""
