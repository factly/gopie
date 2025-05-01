from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    success: bool = Field(..., description="Whether the upload was successful")
    message: str = Field(..., description="Message about the upload status")


class UploadSchemaRequest(BaseModel):
    project_id: str
    dataset_id: str
    file_path: str
