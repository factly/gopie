import uuid

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.models.chat import EventChunkData, Role
from app.models.router import Message
from app.workflow.agent import agent_graph
from app.workflow.events.handle_events_stream import EventStreamHandler


async def stream_graph_updates(
    messages: list[Message],
    user: str,
    trace_id: str,
    chat_id: str,
    dataset_ids: list[str] | None = None,
    project_ids: list[str] | None = None,
    model_id: str | None = None,
):
    """
    Stream graph updates for user input with event tracking.

    Args:
        messages: A list of messages in the conversation
        dataset_ids: Specific dataset IDs to use for the query
        project_ids: Specific project IDs to use for the query
        chat_id: Unique identifier for the chat session
        trace_id: Optional trace ID for tracking
        model_id: Optional model ID for selecting the reasoning model
        user: User identifier
        use_multi_agent: Whether to use multi-agent architecture (None = auto)
        query_complexity: Estimated query complexity for routing decisions

    Yields:
        str: JSON-formatted event data for streaming in SSE format
    """
    if not trace_id:
        trace_id = str(uuid.uuid4())
    if project_ids is None and dataset_ids is None:
        raise ValueError("At least one dataset or project ID must be provided")

    chat_history = [
        convert_to_langchain_message(message) for message in messages[:-1]
    ]

    input_state = {
        "messages": [message.model_dump() for message in messages],
        "dataset_ids": dataset_ids,
        "project_ids": project_ids,
    }

    event_stream_handler = EventStreamHandler()
    metadata = {
        "trace_id": trace_id,
        "chat_id": chat_id,
        "user": user,
    }
    config = RunnableConfig(
        configurable={
            "metadata": metadata,
            "chat_history": chat_history,
        },
    )

    try:
        async for event in agent_graph.astream_events(
            input_state,
            subgraphs=True,
            version="v2",
            config=config,
        ):
            extracted_event_data = event_stream_handler.handle_events_stream(
                event
            )
            if extracted_event_data.role:
                yield extracted_event_data

    except Exception as e:
        output = EventChunkData(
            role=Role.INTERMEDIATE,
            content="Sorry, something went wrong. Please try again later",
            category="error",
        )
        yield output
        logger.exception(e)


def convert_to_langchain_message(message: Message):
    if message.role == "user":
        return HumanMessage(content=message.content)
    elif message.role == "assistant":
        return AIMessage(content=message.content)
    else:
        raise ValueError(f"Unknown role: {message.role}")
