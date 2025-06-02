import json
import time
from typing import Any, AsyncIterable, Literal, cast

from openai.types.chat.chat_completion import ChatCompletion as Response
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk as ResponseChunk,
)
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)
from openai.types.chat.completion_create_params import (
    CompletionCreateParamsNonStreaming as RequestNonStreaming,
)
from openai.types.chat.completion_create_params import (
    CompletionCreateParamsStreaming as RequestStreaming,
)

from app.core.log import logger
from app.models.chat import (
    OpenAiStreamingState,
    Role,
    StructuredChatStreamChunk,
    ToolMessage,
)
from app.models.router import Message, QueryRequest


def _initialize_streaming_state(
    model: str | None = None, trace_id: str = ""
) -> OpenAiStreamingState:
    return OpenAiStreamingState(
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
        last_sent_sql_query=[],
        yield_content=False,
        delta_content="",
        finish_reason="stop",  # Default finish reason
    )


def _process_datasets(
    chunk: StructuredChatStreamChunk, state: OpenAiStreamingState
) -> list[str]:
    current_datasets = []
    if chunk.datasets_used:
        for dataset in chunk.datasets_used:
            if dataset not in state["datasets_used"]:
                state["datasets_used"].append(dataset)
                current_datasets.append(dataset)
    return current_datasets


def _process_sql_query(
    chunk: StructuredChatStreamChunk, state: OpenAiStreamingState
) -> list[str]:
    current_sql_query = []
    if (
        chunk.generated_sql_query
        and chunk.generated_sql_query != state["last_sent_sql_query"]
    ):
        current_sql_query = chunk.generated_sql_query
    return current_sql_query


def _process_messages(
    chunk: StructuredChatStreamChunk, state: OpenAiStreamingState
) -> list[dict[str, str]]:
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


def _create_content_chunk(state: OpenAiStreamingState) -> ResponseChunk:
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
    current_tool_messages: list[dict[str, str]],
    current_datasets: list[str],
    current_sql_query: list[str],
    state: OpenAiStreamingState,
) -> list[dict[str, Any]]:
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
    tool_calls: list[dict[str, Any]], state: OpenAiStreamingState
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


def _create_final_chunk(state: OpenAiStreamingState) -> ResponseChunk:
    final_chunk = {
        "id": state["completion_id"],
        "object": "chat.completion.chunk",
        "created": state["created"],
        "model": state["model"],
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": state.get("finish_reason", "stop"),
            }
        ],
    }

    return ResponseChunk(
        id=final_chunk["id"],
        object=final_chunk["object"],
        created=final_chunk["created"],
        model=final_chunk["model"],
        choices=final_chunk["choices"],
    )


def from_openai_format(
    request: RequestNonStreaming | RequestStreaming,
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
            content=str(message.get("content", "")),
        )
        for message in request.get("messages")
    ]

    metadata = request.get("metadata")
    if metadata:
        project_ids: list[str] = []
        dataset_ids: list[str] = []
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
    trace_id: str,
    model: str | None = None,
) -> Response:
    """
    Args:
        response_chunks: List of internal response chunks
        model: The model name to include in the response
        finish_reason: The reason the completion finished

    Returns:
        Response: OpenAI-compatible response
    """
    state = _initialize_streaming_state(model or "", trace_id)

    async for chunk in response_chunks:
        _process_datasets(chunk, state)
        if chunk.generated_sql_query:
            state["last_sent_sql_query"] = chunk.generated_sql_query

        if chunk.finish_reason:
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
            ChatCompletionMessageToolCall(
                id=f"call_{tool_call_id}",
                type="function",
                function=Function(
                    name="tool_messages",
                    arguments=json.dumps({"messages": state["tool_messages"]}),
                ),
            )
        )

    # Add datasets tool call if any datasets were used
    if state["datasets_used"]:
        tool_call_id += 1
        tool_calls.append(
            ChatCompletionMessageToolCall(
                id=f"call_{tool_call_id}",
                type="function",
                function=Function(
                    name="datasets_used",
                    arguments=json.dumps({"datasets": state["datasets_used"]}),
                ),
            )
        )

    # Add SQL query tool call if there's a query
    if state["last_sent_sql_query"]:
        tool_call_id += 1
        tool_calls.append(
            ChatCompletionMessageToolCall(
                id=f"call_{tool_call_id}",
                type="function",
                function=Function(
                    name="sql_query",
                    arguments=json.dumps(
                        {"query": state["last_sent_sql_query"]}
                    ),
                ),
            )
        )

    # Build the OpenAI response message
    message = ChatCompletionMessage(
        role="assistant",
        content=state["content_so_far"],
        tool_calls=tool_calls if tool_calls else None,
    )

    # Ensure finish_reason is a valid OpenAI literal
    valid_finish_reasons = {
        "stop",
        "length",
        "tool_calls",
        "content_filter",
        "function_call",
    }
    finish_reason_str = (
        state["finish_reason"]
        if state["finish_reason"] in valid_finish_reasons
        else "stop"
    )
    finish_reason = cast(
        Literal[
            "stop", "length", "tool_calls", "content_filter", "function_call"
        ],
        finish_reason_str,
    )

    # Create the final response
    return Response(
        id=state["completion_id"],
        choices=[
            Choice(
                index=0,
                message=message,
                finish_reason=finish_reason,
            )
        ],
        created=state["created"],
        model=state["model"] or "unknown",
        object="chat.completion",
    )


async def _to_openai_streaming_format(
    response_chunks: AsyncIterable[StructuredChatStreamChunk],
    trace_id: str,
    model: str | None = None,
) -> AsyncIterable[ResponseChunk]:
    """
    Args:
        response_chunks: AsyncIterable of internal response chunks
        model: The model name to include in responses
        finish_reason: The reason the completion finished (default: "stop")

    Returns:
        AsyncIterable of ResponseChunk objects in OpenAI streaming format
    """
    state = _initialize_streaming_state(model or "", trace_id)
    try:
        async for chunk in response_chunks:
            current_datasets = _process_datasets(chunk, state)
            current_sql_query = _process_sql_query(chunk, state)
            current_tool_messages = _process_messages(chunk, state)

            if chunk.finish_reason:
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
        yield _create_final_chunk(state)
    except Exception as e:
        yield _create_final_chunk(state)
        logger.exception(e, stack_info=True, stacklevel=3)


async def to_openai_streaming_format(
    response_chunks: AsyncIterable[StructuredChatStreamChunk],
    trace_id: str,
    model: str | None = None,
) -> AsyncIterable[str]:
    """
    Args:
        response_chunks: AsyncIterable of internal response chunks
        model: The model name to include in responses
        finish_reason: The reason the completion finished (default: "stop")
    """
    openai_chunks = _to_openai_streaming_format(
        response_chunks, trace_id, model
    )
    async for chunk in openai_chunks:
        yield f"data: {chunk.model_dump(mode='json')}\n\n"
    yield "data: [DONE]\n\n"
