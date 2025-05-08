from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    success: bool = Field(..., description="Whether the upload was successful")
    message: str = Field(..., description="Message about the upload status")


class UploadSchemaRequest(BaseModel):
    project_id: str
    dataset_id: str


class Message(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    messages: list[Message]
    project_ids: list[str] | None = None
    dataset_ids: list[str] | None = None
    chat_id: str | None = None
    trace_id: str | None = None
