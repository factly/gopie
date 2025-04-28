from app.workflow.graph.graph_stream import stream_graph_updates
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.data import QueryRequest

router = APIRouter()


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
            request.messages, 
            dataset_ids=request.dataset_ids, 
            project_ids=request.project_ids
        ),
        media_type="text/event-stream",
    )
