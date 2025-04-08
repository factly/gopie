from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response model for dataset upload."""

    success: bool = Field(..., description="Whether the upload was successful")
    message: str = Field(..., description="Message about the upload status")


class UploadSchemaRequest(BaseModel):
    project_id: str
    dataset_id: str
    file_path: str


class Dataset_details(BaseModel):
    id: str
    name: str
    alias: str
    description: str
    file_path: str
    format: str
    row_count: int
    size: int
    columns: list
    created_at: str
    updated_at: str
    created_by: str
    updated_by: str
