import json
import logging
import time
from typing import Any, AsyncIterable, Dict, List, TypedDict, Union

from openai.types.chat.chat_completion import ChatCompletion as Response
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk as ResponseChunk,
)
from openai.types.chat.completion_create_params import (
    CompletionCreateParamsNonStreaming as RequestNonStreaming,
)
from openai.types.chat.completion_create_params import (
    CompletionCreateParamsStreaming as RequestStreaming,
)

from app.models.chat import Role, StructuredChatStreamChunk, ToolMessage
from app.models.router import Message, QueryRequest

logger = logging.getLogger(__name__)


class StreamingState(TypedDict):
    completion_id: str
    created: int
    model: str
    tool_messages: list
    datasets_used: list
    content_so_far: str
    chunk_count: int
    tool_call_id: int
    last_sent_tool_messages: list
    last_sent_datasets: list
    last_sent_sql_query: str
    yield_content: bool
    delta_content: str
    finish_reason: str


def _initialize_streaming_state(model: str, trace_id: str) -> StreamingState:
    """Initialize the state dictionary for streaming."""

    return StreamingState(
        completion_id=trace_id,
        created=int(time.time()),
        model=model,
        tool_messages=[],
        datasets_used=[],
        content_so_far="",
        chunk_count=0,
        tool_call_id=0,
        last_sent_tool_messages=[],
        last_sent_datasets=[],
        last_sent_sql_query="",
        yield_content=False,
        delta_content="",
        finish_reason="stop",  # Default finish reason
    )


def _process_datasets(
    chunk: StructuredChatStreamChunk, state: StreamingState
) -> List[str]:
    """Process datasets in the chunk and update state."""
    current_datasets = []
    if chunk.datasets_used:
        for dataset in chunk.datasets_used:
            if dataset not in state["datasets_used"]:
                state["datasets_used"].append(dataset)
                current_datasets.append(dataset)
    return current_datasets


def _process_sql_query(
    chunk: StructuredChatStreamChunk, state: StreamingState
) -> str:
    """Process SQL query in the chunk and update state."""
    current_sql_query = ""
    if (
        chunk.generated_sql_query
        and chunk.generated_sql_query != state["last_sent_sql_query"]
    ):
        current_sql_query = chunk.generated_sql_query
    return current_sql_query


def _process_messages(
    chunk: StructuredChatStreamChunk, state: StreamingState
) -> List[Dict[str, str]]:
    """Process messages in the chunk and update state."""
    current_tool_messages = []

    if (
        chunk.message
        and hasattr(chunk.message, "content")
        and chunk.message.content
    ):
        if isinstance(chunk.message, ToolMessage):
            # Add new tool message
            tool_message = {
                "role": chunk.message.role,
                "category": chunk.message.category,
                "content": chunk.message.content,
            }
            state["tool_messages"].append(tool_message)
            current_tool_messages.append(tool_message)
        elif chunk.message.role == Role.INTERMEDIATE:
            tool_message = {
                "role": chunk.message.role,
                "content": chunk.message.content,
            }
            state["tool_messages"].append(tool_message)
            current_tool_messages.append(tool_message)
        else:
            # For regular text, prepare to stream it out
            delta_content = chunk.message.content
            state["content_so_far"] += delta_content
            state["delta_content"] = delta_content
            state["yield_content"] = True

    return current_tool_messages


def _create_content_chunk(state: StreamingState) -> ResponseChunk:
    """Create a content chunk from the current state."""
    chunk_obj = {
        "id": state["completion_id"],
        "object": "chat.completion.chunk",
        "created": state["created"],
        "model": state["model"],
        "choices": [
            {
                "index": 0,
                "delta": {"content": state["delta_content"]},
                "finish_reason": None,
            }
        ],
    }

    # For the first chunk, include "role": "assistant"
    if state["chunk_count"] == 0:
        chunk_obj["choices"][0]["delta"]["role"] = "assistant"

    state["chunk_count"] += 1

    return ResponseChunk(
        id=chunk_obj["id"],
        object=chunk_obj["object"],
        created=chunk_obj["created"],
        model=chunk_obj["model"],
        choices=chunk_obj["choices"],
    )


def _create_tool_calls(
    current_tool_messages: List[Dict[str, str]],
    current_datasets: List[str],
    current_sql_query: str,
    state: StreamingState,
) -> List[Dict[str, Any]]:
    """Create tool calls based on current data and update state."""
    tool_calls = []

    # Add tool messages as a tool call if there are any new ones
    if current_tool_messages:
        state["tool_call_id"] += 1
        tool_calls.append(
            {
                "index": 0,
                "id": f"call_{state['tool_call_id']}",
                "type": "function",
                "function": {
                    "name": "tool_messages",
                    "arguments": json.dumps(
                        {"messages": current_tool_messages}
                    ),
                },
            }
        )
        state["last_sent_tool_messages"].extend(current_tool_messages)

    # Add datasets tool call if any new datasets were used
    if current_datasets:
        state["tool_call_id"] += 1
        tool_calls.append(
            {
                "index": 0,
                "id": f"call_{state['tool_call_id']}",
                "type": "function",
                "function": {
                    "name": "datasets_used",
                    "arguments": json.dumps({"datasets": current_datasets}),
                },
            }
        )
        state["last_sent_datasets"].extend(current_datasets)

    # Add SQL query tool call if there's a new query
    if current_sql_query:
        state["tool_call_id"] += 1
        tool_calls.append(
            {
                "index": 0,
                "id": f"call_{state['tool_call_id']}",
                "type": "function",
                "function": {
                    "name": "sql_query",
                    "arguments": json.dumps({"query": current_sql_query}),
                },
            }
        )
        state["last_sent_sql_query"] = current_sql_query

    return tool_calls


def _create_tool_call_chunk(
    tool_calls: List[Dict[str, Any]], state: StreamingState
) -> ResponseChunk:
    """Create a tool call chunk from the provided tool calls and state."""
    tool_call_chunk = {
        "id": state["completion_id"],
        "object": "chat.completion.chunk",
        "created": state["created"],
        "model": state["model"],
        "choices": [
            {
                "index": 0,
                "delta": {"tool_calls": tool_calls},
                "finish_reason": None,
            }
        ],
    }

    return ResponseChunk(
        id=tool_call_chunk["id"],
        object=tool_call_chunk["object"],
        created=tool_call_chunk["created"],
        model=tool_call_chunk["model"],
        choices=tool_call_chunk["choices"],
    )


def _create_final_chunk(
    state: StreamingState, finish_reason: str
) -> ResponseChunk:
    """Create the final chunk with finish_reason."""
    final_chunk = {
        "id": state["completion_id"],
        "object": "chat.completion.chunk",
        "created": state["created"],
        "model": state["model"],
        "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
    }

    return ResponseChunk(
        id=final_chunk["id"],
        object=final_chunk["object"],
        created=final_chunk["created"],
        model=final_chunk["model"],
        choices=final_chunk["choices"],
    )


def from_openai_format(
    request: Union[RequestNonStreaming, RequestStreaming]
) -> QueryRequest:
    """
    Convert OpenAI API request format to internal QueryRequest format.
    Handles both streaming and non-streaming requests.

    Args:
        request: Either a streaming or non-streaming OpenAI request

    Returns:
        QueryRequest: Internal request format
    """
    # Convert messages from OpenAI format to internal format
    messages = [
        Message(
            role=message.get("role"),
            content=message.get("content"),
        )
        for message in request.get("messages")
    ]

    metadata = request.get("metadata")
    if metadata:
        project_ids: List[str] = []
        dataset_ids: List[str] = []
        for key, value in metadata.items():
            if key.startswith("project_id"):
                project_ids.extend(value.split(","))
            elif key.startswith("dataset_id"):
                dataset_ids.extend(value.split(","))
    query_params = {
        "messages": messages,
        "model_id": request.get(
            "model"
        ),  # Map OpenAI model to internal model_id
        "dataset_ids": dataset_ids,
        "project_ids": project_ids,
    }

    return QueryRequest(**query_params)


async def to_openai_non_streaming_format(
    response_chunks: AsyncIterable[StructuredChatStreamChunk],
    model: str,
    trace_id: str,
) -> Response:
    """
    Args:
        response_chunks: List of internal response chunks
        model: The model name to include in the response
        finish_reason: The reason the completion finished

    Returns:
        Response: OpenAI-compatible response
    """
    # Initialize state for processing
    state = _initialize_streaming_state(model, trace_id)

    async for chunk in response_chunks:
        # Use the helper functions to process each chunk
        _process_datasets(chunk, state)
        if chunk.generated_sql_query:
            state["last_sent_sql_query"] = chunk.generated_sql_query

        # Check for finish reason in the chunk
        if hasattr(chunk, "finish_reason") and chunk.finish_reason:
            state["finish_reason"] = chunk.finish_reason

        if (
            chunk.message
            and hasattr(chunk.message, "content")
            and chunk.message.content
        ):
            if isinstance(chunk.message, ToolMessage):
                # Process tool message
                tool_message = {
                    "role": chunk.message.role,
                    "category": chunk.message.category,
                    "content": chunk.message.content,
                }
                state["tool_messages"].append(tool_message)
            elif chunk.message.role == Role.INTERMEDIATE:
                # Process tool message
                tool_message = {
                    "role": chunk.message.role,
                    "content": chunk.message.content,
                }
                state["tool_messages"].append(tool_message)
            else:
                # For regular text content
                state["content_so_far"] += chunk.message.content

    # Create tool calls for the non-streaming response
    tool_calls = []
    tool_call_id = 0

    # Add tool messages as a tool call if there are any
    if state["tool_messages"]:
        tool_call_id += 1
        tool_calls.append(
            {
                "id": f"call_{tool_call_id}",
                "type": "function",
                "function": {
                    "index": 0,
                    "name": "tool_messages",
                    "arguments": json.dumps(
                        {"messages": state["tool_messages"]}
                    ),
                },
            }
        )

    # Add datasets tool call if any datasets were used
    if state["datasets_used"]:
        tool_call_id += 1
        tool_calls.append(
            {
                "id": f"call_{tool_call_id}",
                "type": "function",
                "function": {
                    "name": "datasets_used",
                    "arguments": json.dumps(
                        {"datasets": state["datasets_used"]}
                    ),
                },
            }
        )

    # Add SQL query tool call if there's a query
    if state["last_sent_sql_query"]:
        tool_call_id += 1
        tool_calls.append(
            {
                "id": f"call_{tool_call_id}",
                "type": "function",
                "function": {
                    "name": "sql_query",
                    "arguments": json.dumps(
                        {"query": state["last_sent_sql_query"]}
                    ),
                },
            }
        )

    # Build the OpenAI response
    message = {"role": "assistant", "content": state["content_so_far"]}

    # Add tool calls to the message if any exist
    if tool_calls:
        message["tool_calls"] = tool_calls

    # Create the final response
    return Response(
        id=state["completion_id"],
        choices=[
            {
                "index": 0,
                "message": message,
                "finish_reason": state["finish_reason"],
            }
        ],
        created=state["created"],
        model=state["model"],
        object="chat.completion",
    )


async def _to_openai_streaming_format(
    response_chunks: AsyncIterable[StructuredChatStreamChunk],
    model: str,
    trace_id: str,
) -> AsyncIterable[ResponseChunk]:
    """
    Args:
        response_chunks: AsyncIterable of internal response chunks
        model: The model name to include in responses
        finish_reason: The reason the completion finished (default: "stop")

    Returns:
        AsyncIterable of ResponseChunk objects in OpenAI streaming format
    """
    # Initialize state
    state = _initialize_streaming_state(model, trace_id)
    try:
        # Process chunks as they arrive
        async for chunk in response_chunks:
            # Process different parts of the chunk
            current_datasets = _process_datasets(chunk, state)
            current_sql_query = _process_sql_query(chunk, state)
            current_tool_messages = _process_messages(chunk, state)

            # Check for finish reason in the chunk
            if hasattr(chunk, "finish_reason") and chunk.finish_reason:
                state["finish_reason"] = chunk.finish_reason

            # Yield content chunk if there is regular text content
            if state["yield_content"]:
                yield _create_content_chunk(state)
                state["yield_content"] = False

            # Create and yield tool call chunks if needed
            tool_calls = _create_tool_calls(
                current_tool_messages,
                current_datasets,
                current_sql_query,
                state,
            )
            if tool_calls:
                yield _create_tool_call_chunk(tool_calls, state)

        # Yield the final chunk with finish_reason
        yield _create_final_chunk(state, state["finish_reason"])
    except Exception as e:
        yield _create_final_chunk(state, "error")
        logger.exception(e, stack_info=True, stacklevel=3)


async def to_openai_streaming_format(
    response_chunks: AsyncIterable[StructuredChatStreamChunk],
    model: str,
    trace_id: str,
) -> AsyncIterable[str]:
    """
    Args:
        response_chunks: AsyncIterable of internal response chunks
        model: The model name to include in responses
        finish_reason: The reason the completion finished (default: "stop")
    """
    openai_chunks = _to_openai_streaming_format(
        response_chunks, model, trace_id
    )
    async for chunk in openai_chunks:
        yield f"data: {chunk.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"
