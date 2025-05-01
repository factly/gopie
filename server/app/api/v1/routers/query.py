from app.models.data import QueryRequest
from app.workflow.graph.graph_stream import stream_graph_updates
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/")
async def root():
    """Entry point for the application."""
    return {"message": "Welcome to the Database Agent API"}


@router.post("/query")
async def query(request: QueryRequest):
    """
    Streams the agent's responses as Server-Sent Events (SSE) based on the input messages and selected datasets or projects.

    - `messages`: A list of user-assistant messages forming the conversation history.
    - `project_ids` (optional): List of project IDs. All datasets under these projects will be included.
    - `dataset_ids` (optional): List of individual dataset IDs to query directly.
    """

    return StreamingResponse(
        stream_graph_updates(
            request.messages,
            dataset_ids=request.dataset_ids,
            project_ids=request.project_ids,
        ),
        media_type="text/event-stream",
    )
