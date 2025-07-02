from typing import Any

from langchain_core.runnables.schema import StreamEvent

from app.models.chat import EventChunkData, ExtraData, Role


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

        content = None
        category = None
        extra_data = None

        role = Role(role_value) if role_value else None

        if event_type.startswith("on_tool"):
            role = Role.INTERMEDIATE
            content, category, should_display_tool = self._handle_tool_events(
                event
            )
            if not should_display_tool:
                return self._create_empty_event_data()

        elif self._is_custom_event(event_type):
            (
                content,
                extra_data,
            ) = self._handle_custom_events(event, progress_message)
            role = Role.INTERMEDIATE

        elif not (role and self._is_chat_model_event(event_type)):
            return self._create_empty_event_data()

        elif self._is_chat_model_event(event_type):
            content = self._handle_chat_model_events(
                event_type, event, role, progress_message
            )
            if content is None:
                return self._create_empty_event_data()

        if not content and content != "":
            content = progress_message

        return EventChunkData(
            role=role,
            content=content,
            category=category,
            extra_data=extra_data,
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
            category=None,
            extra_data=None,
        )

    def _handle_chat_model_events(
        self,
        event_type: str,
        event: StreamEvent,
        role: Role,
        progress_message: str,
    ) -> str | None:
        content = None

        if event_type == "on_chat_model_start":
            content = ""

            if role == Role.INTERMEDIATE:
                self._intermediate_stream_sent = False

        elif event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk", None)

            if role == Role.INTERMEDIATE:
                if self._intermediate_stream_sent:
                    return None
                else:
                    self._intermediate_stream_sent = True
                    content = progress_message

            elif role == Role.AI and chunk and chunk.content:
                content = chunk.content

        elif event_type == "on_chat_model_end":
            content = ""

        return content

    def _handle_custom_events(
        self, event: StreamEvent, progress_message: str
    ) -> tuple[str, ExtraData | None]:
        extra_data = None
        event_data = event.get("data", {})
        content = event_data.get("content", "")
        data_name = event_data.get("name", "")
        if data_name:
            data_args = event_data.get("values", {})
            extra_data = ExtraData(name=data_name, args=data_args)
        if not content:
            content = progress_message
        return content, extra_data

    def _handle_tool_events(self, event: StreamEvent) -> tuple[str, str, bool]:
        content = event.get("metadata", {}).get("tool_text", "Using Tool")
        category = event.get("metadata", {}).get("tool_category", "")
        should_display_tool = event.get("metadata", {}).get(
            "should_display_tool", False
        )

        return content, category, should_display_tool
