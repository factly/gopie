from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    """Schema for a database column."""
    name: str = Field(..., description="Name of the column")
    type: str = Field(..., description="Data type of the column")
    description: Optional[str] = Field(None, description="Description of the column")
    sample_values: Optional[List[str]] = Field(None, description="Sample values from the column")


class TableSchema(BaseModel):
    """Schema for a database table."""
    name: str = Field(..., description="Name of the table")
    columns: List[ColumnSchema] = Field(..., description="Columns in the table")
    row_count: Optional[int] = Field(None, description="Number of rows in the table")
    description: Optional[str] = Field(None, description="Description of the table")


class DatasetSchema(BaseModel):
    """Schema for a dataset."""
    name: str = Field(..., description="Name of the dataset")
    tables: List[TableSchema] = Field(..., description="Tables in the dataset")
    description: Optional[str] = Field(None, description="Description of the dataset")


class DatasetListResponse(BaseModel):
    """Response model for dataset list."""
    datasets: List[str] = Field(..., description="List of available datasets")


class UploadResponse(BaseModel):
    """Response model for dataset upload."""
    success: bool = Field(..., description="Whether the upload was successful")
    message: str = Field(..., description="Message about the upload status")

class UploadSchemaRequest(BaseModel):
    project_id: str
    dataset_id: str
    file_path: str