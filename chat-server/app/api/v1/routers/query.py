import uuid
from typing import Union

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.openai_compatibility import (
    RequestNonStreaming,
    RequestStreaming,
    from_openai_format,
    to_openai_non_streaming_format,
    to_openai_streaming_format,
)
from app.models.router import QueryRequest
from app.workflow.graph.graph_stream import (
    stream_graph_updates,
    stream_graph_updates_json,
)

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Welcome to the Database Agent API"}


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
    - `chat_id` (optional): Unique identifier for the chat session.
    - `trace_id` (optional): Unique identifier for tracing the query execution
    - `model_id` (optional): ID of the model to use for reasoning
    """
    trace_id = uuid.uuid4().hex
    return StreamingResponse(
        stream_graph_updates_json(
            request.messages,
            dataset_ids=request.dataset_ids,
            project_ids=request.project_ids,
            chat_id=request.chat_id,
            trace_id=trace_id,
            model_id=request.model_id,
        ),
        media_type="text/event-stream",
    )


@router.post("/chat/completions")
async def create(
    openai_format_request: Union[RequestNonStreaming, RequestStreaming]
):
    request = from_openai_format(openai_format_request)
    trace_id = uuid.uuid4().hex
    if openai_format_request.get("stream"):
        return StreamingResponse(
            to_openai_streaming_format(
                stream_graph_updates(
                    request.messages,
                    dataset_ids=request.dataset_ids,
                    project_ids=request.project_ids,
                    chat_id=request.chat_id,
                    trace_id=trace_id,
                    model_id=request.model_id,
                ),
                model=request.model_id,
                trace_id=trace_id,
            ),
            media_type="text/event-stream",
        )
    return await to_openai_non_streaming_format(
        stream_graph_updates(
            request.messages,
            dataset_ids=request.dataset_ids,
            project_ids=request.project_ids,
            chat_id=request.chat_id,
            trace_id=trace_id,
            model_id=request.model_id,
        ),
        model=request.model_id,
        trace_id=trace_id,
    )
