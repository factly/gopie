import uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from app.utils.adapters.openai.input import (
    RequestNonStreaming,
    RequestStreaming,
    from_openai_format,
)
from app.utils.adapters.openai.output import OpenAIOutputAdapter
from app.workflow.graph.graph_stream import stream_graph_updates

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Welcome to the GoPie Chat Server API"}


@router.post("/chat/completions")
async def create(
    openai_format_request: RequestNonStreaming | RequestStreaming,
):
    """
    Handle chat completion requests, supporting both streaming and non-streaming responses.

    Accepts a chat completion request in OpenAI-compatible format, validates required identifiers,
    and processes the request using an output adapter. Returns either a streaming response for
    real-time updates or a standard response with the generated chat completion, depending on the request parameters.
    Returns an error response if neither project nor dataset IDs are provided.
    """
    request = from_openai_format(openai_format_request)
    trace_id = request.trace_id or uuid.uuid4().hex
    chat_id = request.chat_id or uuid.uuid4().hex
    user = request.user or "gopie.chat.server"
    adapter = OpenAIOutputAdapter(chat_id, trace_id)

    if request.project_ids is None and request.dataset_ids is None:
        return JSONResponse(
            status_code=500,
            content={"error": "At least one dataset or project ID must be provided"},
        )

    if openai_format_request.get("stream"):
        return StreamingResponse(
            adapter.create_chat_completion_stream(
                stream_graph_updates(
                    messages=request.messages,
                    user=user,
                    trace_id=trace_id,
                    chat_id=chat_id,
                    dataset_ids=request.dataset_ids,
                    project_ids=request.project_ids,
                )
            ),
            media_type="text/event-stream",
        )
    return await adapter.create_chat_completion(
        stream_graph_updates(
            messages=request.messages,
            user=user,
            trace_id=trace_id,
            chat_id=chat_id,
            dataset_ids=request.dataset_ids,
            project_ids=request.project_ids,
        )
    )
