import json
import time
from typing import AsyncIterable

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

from app.models.chat import EventChunkData, Role


class OpenAIOutputAdapter:
    chat_id: str
    trace_id: str
    created: int
    model: str = "gopie-chat"
    tool_calls_count: int = 0
    first_chunk: bool = True

    def __init__(self, chat_id: str, trace_id: str):
        self.chat_id = chat_id
        self.trace_id = trace_id
        self.created = int(time.time())

    async def _create_chat_completion_stream(
        self, event_chunks: AsyncIterable[EventChunkData]
    ) -> AsyncIterable[ResponseChunk]:
        async for event_chunk in event_chunks:
            if event_chunk.role:
                chunk = self.event_to_response(event_chunk)
                if chunk:
                    yield chunk
        yield self.create_final_chunk()

    async def create_chat_completion_stream(
        self, event_chunks: AsyncIterable[EventChunkData]
    ) -> AsyncIterable[str]:
        async for chunk in self._create_chat_completion_stream(event_chunks):
            if chunk:
                yield f"data: {chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"

    def create_tool_call_chunk(
        self, event_chunk: EventChunkData
    ) -> ResponseChunk:
        tool_call_params = None
        if event_chunk.extra_data:
            tool_call_params = {
                "name": event_chunk.extra_data.name,
                "arguments": json.dumps(event_chunk.extra_data.args),
            }
        elif event_chunk.category:
            tool_message = {
                "role": event_chunk.role,
                "category": event_chunk.category,
                "content": event_chunk.content,
            }
            tool_call_params = {
                "name": "tool_messages",
                "arguments": json.dumps(tool_message),
            }
        elif event_chunk.role == Role.INTERMEDIATE:
            if not event_chunk.content:
                return None
            tool_message = {
                "role": event_chunk.role,
                "content": event_chunk.content,
            }
            tool_call_params = {
                "name": "tool_messages",
                "arguments": json.dumps(tool_message),
            }
        if tool_call_params:
            tool_call = {
                "id": f"call_{self.tool_calls_count}",
                "index": self.tool_calls_count,
                "type": "function",
                "function": tool_call_params,
            }
            choices = [
                {
                    "index": 0,
                    "delta": {"tool_calls": [tool_call]},
                    "finish_reason": None,
                }
            ]
            self.tool_calls_count += 1
            return ResponseChunk(
                id=self.trace_id,
                object="chat.completion.chunk",
                created=self.created,
                model=self.model,
                choices=choices,
            )

    def event_to_response(self, event_chunk: EventChunkData) -> ResponseChunk:
        should_be_tool_call = (
            (event_chunk.extra_data)
            or (event_chunk.category)
            or (event_chunk.role == Role.INTERMEDIATE)
        )
        if should_be_tool_call:
            tool_call_chunk = self.create_tool_call_chunk(event_chunk)
            return tool_call_chunk
        else:
            choices = [
                {
                    "index": 0,
                    "delta": {"content": event_chunk.content},
                    "finish_reason": None,
                }
            ]
            if self.first_chunk:
                self.first_chunk = False
                choices[0]["delta"]["role"] = "assistant"
        return ResponseChunk(
            id=self.trace_id,
            object="chat.completion.chunk",
            created=self.created,
            model=self.model,
            choices=choices,
        )

    def create_final_chunk(self) -> ResponseChunk:
        return ResponseChunk(
            id=self.trace_id,
            object="chat.completion.chunk",
            created=self.created,
            model=self.model,
            choices=[
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        )

    async def create_chat_completion(
        self, event_chunks: AsyncIterable[EventChunkData]
    ) -> Response:
        tool_calls = []
        content = ""

        async for completion_chunk in self._create_chat_completion_stream(
            event_chunks
        ):
            if completion_chunk.choices[0].delta.content:
                content += completion_chunk.choices[0].delta.content
            if completion_chunk.choices[0].delta.tool_calls:
                for tool_call in completion_chunk.choices[0].delta.tool_calls:
                    call_id = tool_call.id
                    tool_calls.append(
                        ChatCompletionMessageToolCall(
                            id=call_id,
                            type="function",
                            function=Function(
                                name=tool_call.function.name,
                                arguments=tool_call.function.arguments,
                            ),
                        )
                    )
        message = ChatCompletionMessage(
            role="assistant",
            content=content,
            tool_calls=tool_calls,
        )
        return Response(
            id=self.trace_id,
            object="chat.completion",
            created=self.created,
            model=self.model,
            choices=[
                Choice(
                    index=0,
                    message=message,
                    finish_reason="stop",
                )
            ],
        )
