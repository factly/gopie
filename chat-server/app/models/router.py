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
    user: str | None = None
    chat_id: str | None = None
    trace_id: str | None = None
    model_id: str | None = None


class ModelInfo(BaseModel):
    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Display name for the model")
    provider: str = Field(
        ..., description="Model provider (e.g., OpenAI, Google)"
    )
    description: str = Field(..., description="Brief description of the model")
    is_default: bool = Field(
        False, description="Whether this is the default model"
    )
