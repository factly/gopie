from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ColumnDetails(BaseModel):
    column_name: str
    column_type: str
    default: Optional[Any] = None
    extra: Optional[Any] = None
    key: Optional[Any] = None
    null: str


class ProjectDetails(BaseModel):
    id: str
    name: str
    description: str
    custom_prompt: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class DatasetDetails(BaseModel):
    id: str
    name: str
    alias: str
    description: str
    row_count: Optional[int] = None
    columns: Optional[list[ColumnDetails]] = None
    size: Optional[int] = None
    file_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    custom_prompt: Optional[str] = None
    sql_query: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class ColumnValueMatching(BaseModel):
    class VerifiedValue(BaseModel):
        value: str
        match_type: str = "exact"
        found_in_database: bool

    class SuggestedAlternative(BaseModel):
        requested_value: str
        match_type: str = "fuzzy"
        found_similar_values: bool
        similar_values: list[str] = []
        match_source: str | None = None
        relevance_score: float | None = None
        is_relevant: bool | None = None
        error_message: str | None = None

    class ColumnAnalysis(BaseModel):
        column_name: str
        verified_values: list["ColumnValueMatching.VerifiedValue"] = []
        suggested_alternatives: list["ColumnValueMatching.SuggestedAlternative"] = []

    class DatasetAnalysis(BaseModel):
        dataset_name: str
        columns_analyzed: list["ColumnValueMatching.ColumnAnalysis"] = []

    analysis_type: str = "column_value_verification"
    description: str = "Results of verifying column values across datasets"
    datasets: dict[str, "ColumnValueMatching.DatasetAnalysis"] = {}
    summary: str = ""
