from typing import List, Optional

from app.workflow.graph.graph_stream import stream_graph_updates
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class QueryRequest(BaseModel):
    user_input: str
    project_ids: Optional[List[str]] = None
    dataset_ids: Optional[List[str]] = None

    class Config:
        schema_extra = {
            "example": {
                "user_input": "What is the average salary in the company?",
                "project_ids": ["proj1", "proj2"],
                "dataset_ids": ["ds1", "ds2"]
            }
        }


@router.get("/")
async def root():
    """Entry point for the application."""
    return {"message": "Welcome to the Database Agent API"}


@router.post("/query")
async def query(request: QueryRequest):
    """Stream the agent's processing events as Server-Sent Events.

    Args:
        request: Request body containing user input and optional project/dataset IDs
    """

    return StreamingResponse(
        stream_graph_updates(
            request.user_input, 
            dataset_ids=request.dataset_ids, 
            project_ids=request.project_ids
        ),
        media_type="text/event-stream",
    )
