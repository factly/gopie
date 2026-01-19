from typing import Optional, Tuple

from langchain_core.runnables.schema import StreamEvent

from app.core.log import custom_logger as logger
from app.models.chat import EventChunkData, ExtraData, Role

CHAT_MODEL_EVENTS = {"on_chat_model_start", "on_chat_model_stream", "on_chat_model_end"}
CUSTOM_EVENT = "on_custom_event"
TOOL_EVENT_PREFIX = "on_tool"
TOOL_START_EVENT = "on_tool_start"


class EventStreamHandler:
    def handle_events_stream(
        self,
        event: StreamEvent,
    ) -> EventChunkData:
        """
        Process a streaming event and convert it to EventChunkData.

        Args:
            event: The streaming event dictionary

        Returns:
            EventChunkData containing the processed event information
        """
        try:
            event_type = event.get("event", "")
            if not event_type:
                return self._create_empty_event_data()

            event_metadata = event.get("metadata", {})
            role_value = event_metadata.get("role")

            role = Role(role_value) if role_value else None
            if not role and (
                self._is_custom_event(event_type) or event_type.startswith(TOOL_EVENT_PREFIX)
            ):
                role = Role.INTERMEDIATE
            elif not role:
                return self._create_empty_event_data()

            content: Optional[str] = None
            category: Optional[str] = None
            extra_data: Optional[ExtraData] = None

            if event_type.startswith(TOOL_EVENT_PREFIX):
                role = Role.INTERMEDIATE
                content, category, should_display_tool = self._handle_tool_events(event)
                if not should_display_tool:
                    return self._create_empty_event_data()

            elif self._is_custom_event(event_type):
                content, extra_data = self._handle_custom_events(event)

            elif self._is_chat_model_event(event_type):
                content = self._handle_chat_model_events(event_type, event, role)
                if content is None:
                    return self._create_empty_event_data()

            return EventChunkData(
                role=role,
                content=content or "",
                category=category,
                extra_data=extra_data,
            )

        except Exception as e:
            logger.exception(e)
            return self._create_empty_event_data()

    def _is_chat_model_event(self, event_type: str) -> bool:
        return event_type in CHAT_MODEL_EVENTS

    def _is_custom_event(self, event_type: str) -> bool:
        return event_type == CUSTOM_EVENT

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
    ) -> Optional[str]:
        if event_type == "on_chat_model_start":
            return ""

        elif event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                return chunk.content
            return None

        elif event_type == "on_chat_model_end":
            return "\n"

        return None

    def _handle_custom_events(self, event: StreamEvent) -> Tuple[str, Optional[ExtraData]]:
        event_data = event.get("data", {})
        content = event_data.get("content", "")
        data_name = event_data.get("name", "")

        extra_data = None
        if data_name:
            data_args = event_data.get("values", {})
            extra_data = ExtraData(name=data_name, args=data_args)

        return content, extra_data

    def _handle_tool_events(self, event: StreamEvent) -> Tuple[str, str, bool]:
        event_type = event.get("event", "")
        if event_type != TOOL_START_EVENT:
            return "", "", False

        metadata = event.get("metadata", {})
        content = metadata.get("tool_text", "Using Tool")
        category = metadata.get("tool_category", "")
        should_display_tool = metadata.get("should_display_tool", False)

        return content, category, should_display_tool
