import json
import uuid

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.models.chat import Error, StructuredChatStreamChunk
from app.models.router import Message
from app.workflow.events.dispatcher import AgentEventDispatcher
from app.workflow.events.handle_events_stream import EventStreamHandler
from app.workflow.graph.multi_dataset_graph import multi_dataset_graph
from app.workflow.graph.single_dataset_graph import simple_graph


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

    chat_history = [
        convert_to_langchain_message(message) for message in messages[:-1]
    ]

    input_state = {
        "messages": [message.model_dump() for message in messages],
        "dataset_ids": dataset_ids,
        "project_ids": project_ids,
    }

    event_stream_handler = EventStreamHandler()

    config = RunnableConfig(
        configurable={
            "model_id": model_id,
            "trace_id": trace_id,
            "chat_history": chat_history,
            "user": user,
        },
    )

    dataset_count = len(dataset_ids) if dataset_ids else 0
    selected_graph = (
        simple_graph if dataset_count == 1 else multi_dataset_graph
    )

    try:
        async for event in selected_graph.astream_events(
            input_state,
            version="v2",
            config=config,
        ):
            extracted_event_data = event_stream_handler.handle_events_stream(
                event
            )

            agent_event_dispatcher = AgentEventDispatcher()

            if extracted_event_data.role:
                chunk = agent_event_dispatcher.dispatch_event(
                    chat_id=chat_id,
                    trace_id=trace_id,
                    role=extracted_event_data.role,
                    agent_node=extracted_event_data.graph_node,
                    chunk_type=extracted_event_data.type,
                    content=extracted_event_data.content,
                    datasets_used=extracted_event_data.datasets_used,
                    generated_sql_query=(
                        extracted_event_data.generated_sql_query
                    ),
                    tool_category=extracted_event_data.category,
                )

                logger.debug(
                    json.dumps(chunk.model_dump(mode="json"), indent=2)
                )

                yield chunk

    except Exception as e:
        error = Error(
            type="error",
            message="Sorry, something went wrong. Please try again later",
        )
        output = StructuredChatStreamChunk(
            chat_id=chat_id, error=error, finish_reason="error"
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


async def stream_graph_updates_json(
    *args,
    **kwargs,
):
    async for chunk in stream_graph_updates(*args, **kwargs):
        yield "data: " + json.dumps(chunk.model_dump(mode="json")) + "\n \n"
