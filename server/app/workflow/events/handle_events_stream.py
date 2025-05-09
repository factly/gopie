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


def handle_events_stream(
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

    if event_type == "on_tool_start":
        tool_text = event.get("metadata", {}).get("tool_text", "Using Tool")
        category = event.get("metadata", {}).get("tool_category", "")

        role = Role.SYSTEM
        content = tool_text
        type = ChunkType.BODY
        category = category
    elif event_type == "on_chat_model_start":

        if (
            graph_node == AgentNode.GENERATE_RESULT.value
            or graph_node == AgentNode.MAX_ITERATIONS_REACHED.value
        ):
            role = Role.AI
        else:
            role = Role.INTERMEDIATE

        content = ""
        type = ChunkType.START
    elif event_type == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk", {})

        if (
            chunk
            and chunk.content  # type: ignore
            and (
                graph_node == AgentNode.GENERATE_RESULT.value
                or graph_node == AgentNode.MAX_ITERATIONS_REACHED.value
            )
        ):
            content = chunk.content  # type: ignore
            role = Role.AI
        else:
            role = Role.INTERMEDIATE

        type = ChunkType.STREAM
    elif event_type == "on_chat_model_end":
        if (
            graph_node == AgentNode.GENERATE_RESULT.value
            or graph_node == AgentNode.MAX_ITERATIONS_REACHED.value
        ):
            role = Role.AI
        else:
            role = Role.INTERMEDIATE

        content = ""
        type = ChunkType.END

    if event_type == "on_custom_event":
        role = Role.INTERMEDIATE
        type = ChunkType.STREAM

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
