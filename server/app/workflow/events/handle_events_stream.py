import json
import logging
from enum import Enum

from langchain_core.runnables.schema import StreamEvent

from app.models.chat import AgentNode, ChunkType, EventChunkData


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


INCLUDED_GRAPH_NODES = [
    "generate_subqueries",
    "identify_datasets",
    "plan_query",
    "execute_query",
    "generate_result",
    "max_iterations_reached",
    "tools",
]


def handle_events_stream(
    event: StreamEvent,
) -> EventChunkData:

    event_type = event["event"]
    graph_node = event.get("metadata", {}).get("langgraph_node", "Unknown")

    role = None
    content = None
    type = ChunkType.BODY
    category = None
    datasets_used = None
    generate_sql_query = None

    if graph_node not in INCLUDED_GRAPH_NODES:
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

        role = "system"
        content = tool_text
        type = ChunkType.BODY
        category = category
    elif event_type == "on_chat_model_start":
        role = "ai"
        content = ""
        type = ChunkType.START
    elif event_type == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk", {})
        if chunk and chunk.content and graph_node == "generate_result":
            content = chunk.content
        type = ChunkType.STREAM
        role = "ai"
    elif event_type == "on_chat_model_end":
        role = "ai"
        content = ""
        type = ChunkType.END
    elif event_type == "on_custom_event":
        event_data = event.get("data", {})
        logging.info(f"event_data: {event_data}")

    return EventChunkData(
        role=role,
        graph_node=AgentNode(graph_node),
        content=content,
        type=type,
        category=category,
        datasets_used=datasets_used,
        generate_sql_query=generate_sql_query,
    )
