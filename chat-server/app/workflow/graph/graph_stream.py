from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.models.chat import EventChunkData, Role
from app.models.router import Message
from app.workflow.agent.graph import agent_graph
from app.workflow.events.handle_events_stream import EventStreamHandler
from app.utils.graph_utils.extract_user_input import extract_user_input


async def stream_graph_updates(
    messages: list[Message],
    user: str,
    trace_id: str,
    chat_id: str,
    dataset_ids: list[str] | None = None,
    project_ids: list[str] | None = None,
):
    """
    Asynchronously streams graph-based agent updates in response to user messages, yielding event data suitable for Server-Sent Events (SSE).
    
    Raises:
        ValueError: If neither dataset_ids nor project_ids are provided.
    
    Yields:
        EventChunkData: Structured event data containing graph update information for the client.
    """
    if project_ids is None and dataset_ids is None:
        raise ValueError("At least one dataset or project ID must be provided")

    chat_history = [message.model_dump() for message in messages[:-1]]
    user_input = extract_user_input(messages)

    input_state = {
        "messages": [message.model_dump() for message in messages],
        "dataset_ids": dataset_ids,
        "project_ids": project_ids,
        "initial_user_query": user_input,
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
            extracted_event_data = event_stream_handler.handle_events_stream(event)
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
