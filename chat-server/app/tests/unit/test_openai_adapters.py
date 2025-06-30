"""Tests for OpenAI adapters."""

import json
from unittest.mock import Mock

import pytest

from app.models.chat import EventChunkData, Role
from app.models.router import QueryRequest
from app.utils.adapters.openai.input import from_openai_format
from app.utils.adapters.openai.output import OpenAIOutputAdapter


class TestOpenAIInputAdapter:
    """Test cases for OpenAI input adapter."""

    def test_from_openai_format_basic_request(self):
        """Test converting basic OpenAI request format."""
        openai_request = {
            "messages": [
                {"role": "user", "content": "Hello, how are you?"},
                {"role": "assistant", "content": "I'm doing well!"},
            ],
            "model": "gpt-4",
            "user": "test_user_123",
        }

        result = from_openai_format(openai_request)

        assert isinstance(result, QueryRequest)
        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[0].content == "Hello, how are you?"
        assert result.messages[1].role == "assistant"
        assert result.messages[1].content == "I'm doing well!"
        assert result.model_id == "gpt-4"
        assert result.user == "test_user_123"
        assert result.dataset_ids == []
        assert result.project_ids == []

    def test_from_openai_format_with_metadata(self):
        """Test converting OpenAI request with metadata."""
        openai_request = {
            "messages": [{"role": "user", "content": "Show me data"}],
            "model": "gpt-3.5-turbo",
            "metadata": {
                "project_id_1": "proj1,proj2,proj3",
                "dataset_id_1": "ds1,ds2",
                "dataset_id_2": "ds3, ds4 ",
                "other_field": "ignored",
            },
        }

        result = from_openai_format(openai_request)

        assert result.project_ids == ["proj1", "proj2", "proj3"]
        assert result.dataset_ids == ["ds1", "ds2", "ds3", "ds4"]

    def test_from_openai_format_empty_metadata(self):
        """Test converting OpenAI request with empty metadata."""
        openai_request = {
            "messages": [{"role": "user", "content": "Test message"}],
            "model": "gpt-4",
            "metadata": {},
        }

        result = from_openai_format(openai_request)

        assert result.project_ids == []
        assert result.dataset_ids == []

    def test_from_openai_format_no_metadata(self):
        """Test converting OpenAI request without metadata."""
        openai_request = {
            "messages": [{"role": "user", "content": "Test message"}],
            "model": "gpt-4",
        }

        result = from_openai_format(openai_request)

        assert result.project_ids == []
        assert result.dataset_ids == []
        assert result.user is None

    def test_from_openai_format_with_empty_content(self):
        """Test converting OpenAI request with empty message content."""
        openai_request = {
            "messages": [
                {"role": "user", "content": ""},
                {"role": "user"},  # No content field
            ],
            "model": "gpt-4",
        }

        result = from_openai_format(openai_request)

        assert len(result.messages) == 2
        assert result.messages[0].content == ""
        assert result.messages[1].content == ""

    def test_from_openai_format_mixed_content_types(self):
        """Test converting OpenAI request with different content types."""
        openai_request = {
            "messages": [
                {"role": "user", "content": "Text message"},
                {"role": "user", "content": 123},  # Number content
                {
                    "role": "user",
                    "content": ["array", "content"],
                },  # Array content
            ],
            "model": "gpt-4",
        }

        result = from_openai_format(openai_request)

        assert len(result.messages) == 3
        assert result.messages[0].content == "Text message"
        assert result.messages[1].content == "123"
        assert result.messages[2].content == "['array', 'content']"


class TestOpenAIOutputAdapter:
    """Test cases for OpenAI output adapter."""

    @pytest.fixture
    def output_adapter(self):
        """Create an output adapter instance."""
        return OpenAIOutputAdapter(
            chat_id="test_chat_123", trace_id="test_trace_456"
        )

    def test_output_adapter_initialization(self, output_adapter):
        """Test output adapter initialization."""
        assert output_adapter.chat_id == "test_chat_123"
        assert output_adapter.trace_id == "test_trace_456"
        assert output_adapter.model == "gopie-chat"
        assert output_adapter.tool_calls_count == 0
        assert output_adapter.first_chunk is True
        assert isinstance(output_adapter.created, int)

    def test_create_tool_call_chunk_with_extra_data(self, output_adapter):
        """Test creating tool call chunk with extra data."""
        event_chunk = EventChunkData(
            role=Role.AI,
            content="Tool execution",
            category="tool_call",
            extra_data=Mock(
                name="execute_sql", args={"query": "SELECT * FROM users"}
            ),
        )

        result = output_adapter.create_tool_call_chunk(event_chunk)

        assert result is not None
        assert result.id == "test_trace_456"
        assert result.object == "chat.completion.chunk"
        assert result.model == "gopie-chat"
        assert len(result.choices) == 1

        choice = result.choices[0]
        assert choice["index"] == 0
        assert choice["finish_reason"] is None
        assert "tool_calls" in choice["delta"]

        tool_call = choice["delta"]["tool_calls"][0]
        assert tool_call["id"] == "call_0"
        assert tool_call["type"] == "function"
        assert tool_call["function"]["name"] == "execute_sql"
        assert "SELECT * FROM users" in tool_call["function"]["arguments"]

    def test_create_tool_call_chunk_with_category(self, output_adapter):
        """Test creating tool call chunk with category."""
        event_chunk = EventChunkData(
            role=Role.AI,
            content="Processing data",
            category="data_processing",
        )

        result = output_adapter.create_tool_call_chunk(event_chunk)

        assert result is not None
        tool_call = result.choices[0]["delta"]["tool_calls"][0]
        assert tool_call["function"]["name"] == "tool_messages"

        args = json.loads(tool_call["function"]["arguments"])
        assert args["role"] == Role.AI
        assert args["category"] == "data_processing"
        assert args["content"] == "Processing data"

    def test_create_tool_call_chunk_with_intermediate_role(
        self, output_adapter
    ):
        """Test creating tool call chunk with intermediate role."""
        event_chunk = EventChunkData(
            role=Role.INTERMEDIATE,
            content="Intermediate step",
            category="intermediate",
        )

        result = output_adapter.create_tool_call_chunk(event_chunk)

        assert result is not None
        tool_call = result.choices[0]["delta"]["tool_calls"][0]
        assert tool_call["function"]["name"] == "tool_messages"

        args = json.loads(tool_call["function"]["arguments"])
        assert args["role"] == Role.INTERMEDIATE
        assert args["content"] == "Intermediate step"

    def test_create_tool_call_chunk_with_empty_intermediate(
        self, output_adapter
    ):
        """Test creating tool call chunk with empty intermediate content."""
        event_chunk = EventChunkData(
            role=Role.INTERMEDIATE,
            content="",
            category="intermediate",
        )

        result = output_adapter.create_tool_call_chunk(event_chunk)

        assert result is None

    def test_event_to_response_regular_content(self, output_adapter):
        """Test converting regular event to response chunk."""
        event_chunk = EventChunkData(
            role=Role.ASSISTANT,
            content="This is a regular response",
        )

        result = output_adapter.event_to_response(event_chunk)

        assert result is not None
        assert result.id == "test_trace_456"
        assert result.object == "chat.completion.chunk"

        choice = result.choices[0]
        assert choice["index"] == 0
        assert choice["delta"]["content"] == "This is a regular response"
        assert (
            choice["delta"]["role"] == "assistant"
        )  # First chunk includes role
        assert choice["finish_reason"] is None

    def test_event_to_response_subsequent_chunks(self, output_adapter):
        """Test that subsequent chunks don't include role."""
        # First chunk
        event_chunk1 = EventChunkData(
            role=Role.ASSISTANT,
            content="First chunk",
        )
        result1 = output_adapter.event_to_response(event_chunk1)
        assert result1.choices[0]["delta"]["role"] == "assistant"

        # Second chunk
        event_chunk2 = EventChunkData(
            role=Role.ASSISTANT,
            content="Second chunk",
        )
        result2 = output_adapter.event_to_response(event_chunk2)
        assert "role" not in result2.choices[0]["delta"]

    def test_create_final_chunk(self, output_adapter):
        """Test creating final chunk."""
        result = output_adapter.create_final_chunk()

        assert result is not None
        assert result.id == "test_trace_456"
        assert result.object == "chat.completion.chunk"

        choice = result.choices[0]
        assert choice["index"] == 0
        assert choice["delta"] == {}
        assert choice["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_create_chat_completion_stream(self, output_adapter):
        """Test creating chat completion stream."""

        async def mock_event_chunks():
            yield EventChunkData(role=Role.ASSISTANT, content="Hello ")
            yield EventChunkData(role=Role.ASSISTANT, content="world!")

        chunks = []
        async for chunk in output_adapter.create_chat_completion_stream(
            mock_event_chunks()
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert chunks[0].startswith("data: ")
        assert chunks[-1] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_create_chat_completion_non_streaming(self, output_adapter):
        """Test creating non-streaming chat completion."""

        async def mock_event_chunks():
            yield EventChunkData(role=Role.ASSISTANT, content="Hello ")
            yield EventChunkData(role=Role.ASSISTANT, content="world!")
            yield EventChunkData(
                role=Role.TOOL,
                content="Tool result",
                extra_data=Mock(name="test_tool", args={"param": "value"}),
            )

        result = await output_adapter.create_chat_completion(
            mock_event_chunks()
        )

        assert result is not None
        assert result.id == "test_trace_456"
        assert result.object == "chat.completion"
        assert result.model == "gopie-chat"

        message = result.choices[0].message
        assert message.role == "assistant"
        assert message.content == "Hello world!"
        assert len(message.tool_calls) == 1

        tool_call = message.tool_calls[0]
        assert tool_call.function.name == "test_tool"
        assert "param" in tool_call.function.arguments

    def test_tool_calls_counter_increment(self, output_adapter):
        """Test that tool calls counter increments properly."""
        # First tool call
        event_chunk1 = EventChunkData(
            role=Role.TOOL,
            content="First tool",
            extra_data=Mock(name="tool1", args={}),
        )
        result1 = output_adapter.create_tool_call_chunk(event_chunk1)
        assert result1.choices[0]["delta"]["tool_calls"][0]["id"] == "call_0"
        assert output_adapter.tool_calls_count == 1

        # Second tool call
        event_chunk2 = EventChunkData(
            role=Role.TOOL,
            content="Second tool",
            extra_data=Mock(name="tool2", args={}),
        )
        result2 = output_adapter.create_tool_call_chunk(event_chunk2)
        assert result2.choices[0]["delta"]["tool_calls"][0]["id"] == "call_1"
        assert output_adapter.tool_calls_count == 2
