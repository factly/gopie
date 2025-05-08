from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.router import QueryRequest
from app.workflow.graph.graph_stream import stream_graph_updates

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Welcome to the Database Agent API"}


@router.post("/query")
async def query(request: QueryRequest):
    """
    Streams the agent's responses as Server-Sent Events (SSE) based on the
    input messages and selected datasets or projects.

    - `messages`: A list of user-assistant messages forming the conversation
                  history.
    - `project_ids` (optional): List of project IDs. Include all datasets under
                                these projects.
    - `dataset_ids` (optional): List of individual dataset IDs to query
                                directly.
    - `chat_id` (optional): Unique identifier for the chat session.
    - `trace_id` (optional): Unique identifier for tracing the query execution
    """

    return StreamingResponse(
        stream_graph_updates(
            request.messages,
            dataset_ids=request.dataset_ids,
            project_ids=request.project_ids,
            chat_id=request.chat_id,
            trace_id=request.trace_id,
        ),
        media_type="text/event-stream",
    )
