import json
from enum import Enum

from langchain_core.runnables.schema import StreamEvent

from app.models.chat import AgentNode, ChunkType, EventChunkData, Role


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        try:
            return obj.__dict__
        except AttributeError:
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            return str(obj)


class EventStreamHandler:
    def __init__(self):
        self._tool_start = False

    def handle_events_stream(
        self,
        event: StreamEvent,
    ) -> EventChunkData:

        event_type = event["event"]
        graph_node = event.get("metadata", {}).get("langgraph_node", "unknown")

        role = None
        content = None
        type = ChunkType.BODY
        category = None
        datasets_used = None
        generate_sql_query = None

        if graph_node not in [node.value for node in AgentNode]:
            return EventChunkData(
                role=role,
                graph_node=AgentNode.UNKNOWN,
                content=content,
                type=type,
                category=category,
            )

        tool_text = event.get("metadata", {}).get("tool_text", "Using Tool")
        category = event.get("metadata", {}).get("tool_category", "")

        if event_type.startswith("on_tool"):
            role = Role.SYSTEM
            category = category
            content = ""

        if event_type == "on_tool_start":
            self._tool_start = True
            type = ChunkType.START
        elif event_type == "on_tool_end":
            self._tool_start = False
            type = ChunkType.END
        elif self._tool_start:
            content = tool_text
            type = ChunkType.STREAM
        else:
            self._tool_start = False

        if event_type == "on_chat_model_start":
            role = self.get_chat_role(graph_node)
            content = ""
            type = ChunkType.START
        elif event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk", None)

            role = self.get_chat_role(graph_node)

            if (
                chunk
                and chunk.content
                and (
                    graph_node == AgentNode.STREAM_UPDATES.value
                    or graph_node == AgentNode.GENERATE_RESULT.value
                )
            ):
                content = chunk.content
            else:
                content = ""

            type = ChunkType.STREAM
        elif event_type == "on_chat_model_end":
            role = self.get_chat_role(graph_node)

            content = ""
            type = ChunkType.END

        if event_type == "on_custom_event":
            role = Role.INTERMEDIATE
            type = ChunkType.BODY

            event_data = event.get("data", {})
            content = event_data.get("content", "")
            datasets_used = event_data.get("datasets", [])
            generate_sql_query = event_data.get("query", "")

        return EventChunkData(
            role=role,
            graph_node=AgentNode(graph_node),
            content=content,
            type=type,
            category=category,
            datasets_used=datasets_used,
            generate_sql_query=generate_sql_query,
        )

    def get_chat_role(self, node: str) -> Role:
        if node in AgentNode.GENERATE_RESULT.value:
            return Role.AI
        return Role.INTERMEDIATE
