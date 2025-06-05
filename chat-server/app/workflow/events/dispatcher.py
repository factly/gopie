from langchain_core.callbacks import BaseCallbackHandler

from app.models.chat import (
    AgentNode,
    ChatTextChunk,
    ChunkType,
    Role,
    StructuredChatStreamChunk,
    ToolMessage,
)


def create_progress_message(agent_node: AgentNode) -> str:
    event_messages = {
        AgentNode.GENERATE_SUBQUERIES: "Breaking down your query into "
        "manageable parts...",
        AgentNode.IDENTIFY_DATASETS: "Identifying relevant datasets...",
        AgentNode.ANALYZE_DATASETS: "Analyzing datasets...",
        AgentNode.PLAN_QUERY: "Planning the database query...",
        AgentNode.STREAM_UPDATES: "",
        AgentNode.GENERATE_RESULT: "",
        AgentNode.TOOLS: "Executing tool...",
        AgentNode.UNKNOWN: "Processing...",
        AgentNode.PROCESS_QUERY: "Processing your query...",
        AgentNode.RESPONSE: ".",
    }

    return event_messages.get(agent_node, "Processing...")


class AgentEventDispatcher(BaseCallbackHandler):
    """Custom event dispatcher for the Dataful Agent."""

    def __init__(self):
        super().__init__()

    def dispatch_event(
        self,
        agent_node: AgentNode,
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
            agent_node: The current node in the agent workflow
            chat_id: Unique identifier for the chat session
            trace_id: Unique identifier for the trace (optional)
            chunk_type: Type of chunk (START, STREAM, END, BODY)
            content: Content to be displayed
            datasets_used: List of datasets used in the query
            generated_sql_query: Generated SQL query if applicable
            tool_category: Tool category if the message is from a tool
        """
        if content is None:
            content = create_progress_message(agent_node)

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
