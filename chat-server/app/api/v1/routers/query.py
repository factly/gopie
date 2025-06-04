import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.router import QueryRequest
from app.utils.adapters.openai_adapter import (
    RequestNonStreaming,
    RequestStreaming,
    from_openai_format,
    to_openai_non_streaming_format,
    to_openai_streaming_format,
)
from app.workflow.graph.multidataset_agent.graph_stream import (
    stream_graph_updates,
    stream_graph_updates_json,
)

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Welcome to the Gopie Chat Server API"}


@router.post("/query")
async def query(request: QueryRequest):
    """
    Streams the agent's responses as Server-Sent Events (SSE) based on the
    input messages and selected datasets or projects.

    - `messages`: A list of user-assistant messages.
    - `project_ids` (optional): List of project IDs. Include all datasets under
                                the projects.
    - `dataset_ids` (optional): List of individual dataset IDs to query
                                directly.
    - `user` (optional): User identifier for tracing the query execution
    - `chat_id` (optional): Unique identifier for the chat session.
    - `trace_id` (optional): Unique identifier for tracing the query execution
    - `model_id` (optional): ID of the model to use for reasoning
    """
    trace_id = uuid.uuid4().hex
    return StreamingResponse(
        stream_graph_updates_json(
            messages=request.messages,
            dataset_ids=request.dataset_ids,
            project_ids=request.project_ids,
            chat_id=request.chat_id,
            trace_id=trace_id,
            model_id=request.model_id,
            user=request.user,
        ),
        media_type="text/event-stream",
    )


@router.post("/chat/completions")
async def create(
    openai_format_request: RequestNonStreaming | RequestStreaming,
):
    request = from_openai_format(openai_format_request)
    trace_id = uuid.uuid4().hex
    if openai_format_request.get("stream"):
        return StreamingResponse(
            to_openai_streaming_format(
                stream_graph_updates(
                    messages=request.messages,
                    dataset_ids=request.dataset_ids,
                    project_ids=request.project_ids,
                    chat_id=request.chat_id,
                    trace_id=trace_id,
                    model_id=request.model_id,
                    user=request.user,
                ),
                trace_id=trace_id,
                model=request.model_id,
            ),
            media_type="text/event-stream",
        )
    return await to_openai_non_streaming_format(
        stream_graph_updates(
            messages=request.messages,
            dataset_ids=request.dataset_ids,
            project_ids=request.project_ids,
            chat_id=request.chat_id,
            trace_id=trace_id,
            model_id=request.model_id,
            user=request.user,
        ),
        trace_id=trace_id,
        model=request.model_id,
    )
