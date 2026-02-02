from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field, model_validator

from app.workflow.graph.nl_to_sql_graph.types import SqlQuery


class UploadResponse(BaseModel):
    success: bool = Field(..., description="Whether the upload was successful")
    message: str = Field(..., description="Message about the upload status")


class UploadSchemaRequest(BaseModel):
    project_id: str
    dataset_id: str
    is_view: bool = False


class QueryRequest(BaseModel):
    messages: list[BaseMessage]
    project_ids: list[str] | None = None
    dataset_ids: list[str] | None = None
    user: str | None = None
    chat_id: str | None = None
    trace_id: str | None = None
    model_id: str | None = None


class FetchSqlRequest(BaseModel):
    project_ids: list[str] | None = Field(default=None, description="List of project IDs")
    dataset_ids: list[str] | None = Field(default=None, description="List of dataset IDs")
    description: str = Field(..., description="Natural language description of the data to query")


class FetchSqlResponse(BaseModel):
    sql_queries: list[SqlQuery] = Field(default_factory=list, description="Generated SQL queries")
    message: str | None = Field(
        default=None, description="Message when no SQL queries are generated"
    )

    @model_validator(mode="after")
    def validate_response(self) -> "FetchSqlResponse":
        if not self.sql_queries and not self.message:
            self.message = "Unable to generate SQL queries for the given description."
        return self
