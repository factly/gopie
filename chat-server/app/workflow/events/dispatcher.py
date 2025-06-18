from langchain_core.callbacks import BaseCallbackHandler

from app.models.chat import (
    ChatTextChunk,
    ChunkType,
    Role,
    StructuredChatStreamChunk,
    ToolMessage,
)
from app.workflow.events.node_config_manager import node_config_manager


def create_progress_message(node_name: str) -> str:
    return node_config_manager.get_progress_message(node_name)


class AgentEventDispatcher(BaseCallbackHandler):
    def __init__(self):
        super().__init__()

    def dispatch_event(
        self,
        node_name: str,
        chunk_type: ChunkType,
        role: Role,
        chat_id: str | None = None,
        trace_id: str | None = None,
        content: str | None = None,
        datasets_used: list[str] | None = None,
        generated_sql_query: list[str] | None = None,
        tool_category: str | None = None,
    ) -> StructuredChatStreamChunk:
        """
        Dispatch an event with the appropriate chunk type and content.

        Args:
            node_name: The name of the current node in the workflow
            chat_id: Unique identifier for the chat session
            trace_id: Unique identifier for the trace (optional)
            chunk_type: Type of chunk (START, STREAM, END, BODY)
            content: Content to be displayed
            datasets_used: List of datasets used in the query
            generated_sql_query: Generated SQL query if applicable
            tool_category: Tool category if the message is from a tool
        """
        if content is None:
            content = create_progress_message(node_name)

        if tool_category:
            message = ToolMessage(
                role=role,
                content=content,
                type=chunk_type,
                category=tool_category,
            )
        else:
            message = ChatTextChunk(
                role=role, content=content, type=chunk_type
            )

        chunk = StructuredChatStreamChunk(
            chat_id=chat_id,
            trace_id=trace_id,
            message=message,
            datasets_used=datasets_used,
            generated_sql_query=generated_sql_query,
        )

        return chunk
