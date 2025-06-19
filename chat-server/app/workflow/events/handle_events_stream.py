from typing import Any

from langchain_core.runnables.schema import StreamEvent

from app.models.chat import ChunkType, EventChunkData, Role


class EventStreamHandler:
    def __init__(self):
        self._intermediate_stream_sent = False

    def handle_events_stream(
        self,
        event: Any,
    ) -> EventChunkData:
        event_type = event["event"]

        event_metadata = event.get("metadata", {})
        role_value = event_metadata.get("role", None)
        progress_message = event_metadata.get("progress_message", "")

        type = ChunkType.BODY
        content = None
        category = None
        datasets_used = None
        generated_sql_query = None

        role = Role(role_value) if role_value else None

        if event_type.startswith("on_tool"):
            role = Role.INTERMEDIATE
            content, type, category = self._handle_tool_events(event)

        elif self._is_custom_event(event_type):
            type = ChunkType.BODY
            (
                content,
                datasets_used,
                generated_sql_query,
            ) = self._handle_custom_events(event, progress_message)
            role = Role.INTERMEDIATE

        elif not (role and self._is_chat_model_event(event_type)):
            return self._create_empty_event_data()

        elif self._is_chat_model_event(event_type):
            content, type = self._handle_chat_model_events(
                event_type, event, role, progress_message
            )
            if content is None and type == ChunkType.STREAM:
                return self._create_empty_event_data()

        if not content and content != "":
            content = progress_message

        return EventChunkData(
            role=role,
            content=content,
            type=type,
            category=category,
            datasets_used=datasets_used,
            generated_sql_query=generated_sql_query,
        )

    def _is_chat_model_event(self, event_type: str) -> bool:
        return event_type in [
            "on_chat_model_start",
            "on_chat_model_stream",
            "on_chat_model_end",
        ]

    def _is_custom_event(self, event_type: str) -> bool:
        return event_type == "on_custom_event"

    def _create_empty_event_data(self) -> EventChunkData:
        return EventChunkData(
            role=None,
            content="",
            type=ChunkType.BODY,
            category=None,
        )

    def _handle_chat_model_events(
        self,
        event_type: str,
        event: StreamEvent,
        role: Role,
        progress_message: str,
    ) -> tuple[str | None, ChunkType]:
        content = None
        type = ChunkType.BODY

        if event_type == "on_chat_model_start":
            content = ""
            type = ChunkType.START

            if role == Role.INTERMEDIATE:
                self._intermediate_stream_sent = False

        elif event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk", None)
            type = ChunkType.STREAM

            if role == Role.INTERMEDIATE:
                if self._intermediate_stream_sent:
                    return None, type
                else:
                    self._intermediate_stream_sent = True
                    content = progress_message

            elif role == Role.AI and chunk and chunk.content:
                content = chunk.content

        elif event_type == "on_chat_model_end":
            content = ""
            type = ChunkType.END

        return content, type

    def _handle_custom_events(
        self, event: StreamEvent, progress_message: str
    ) -> tuple[str, list, list]:
        event_data = event.get("data", {})
        content = event_data.get("content", "")
        datasets_used = event_data.get("identified_datasets", [])
        generated_sql_query = event_data.get("queries", [])

        if not content:
            content = progress_message

        return content, datasets_used, generated_sql_query

    def _handle_tool_events(
        self, event: StreamEvent
    ) -> tuple[str, ChunkType, str]:
        event_type = event["event"]
        tool_text = event.get("metadata", {}).get("tool_text", "Using Tool")
        category = event.get("metadata", {}).get("tool_category", "")

        content = tool_text
        type = ChunkType.BODY

        if event_type == "on_tool_start":
            type = ChunkType.START
        elif event_type == "on_tool_end":
            type = ChunkType.END

        return content, type, category
