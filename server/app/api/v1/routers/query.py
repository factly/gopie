from typing import List, Optional

from app.workflow.graph.graph_stream import stream_graph_updates
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/")
async def root():
    """Entry point for the application."""
    return {"message": "Welcome to the Database Agent API"}


@router.post("/query")
async def query(
    user_input: str = Query(
        ..., description="The natural language query from the user"
    ),
    project_ids: Optional[List[str]] = Query(None, description="List of project IDs"),
    dataset_ids: Optional[List[str]] = Query(None, description="List of dataset IDs"),
):
    """Stream the agent's processing events as Server-Sent Events.

    Args:
        user_input: The natural language query from the user
        project_ids (List[str], optional): List of project IDs to use for the query
        dataset_ids (List[str], optional): List of dataset IDs to use for the query
    """

    return StreamingResponse(
        stream_graph_updates(
            user_input, dataset_ids=dataset_ids, project_ids=project_ids
        ),
        media_type="text/event-stream",
    )
