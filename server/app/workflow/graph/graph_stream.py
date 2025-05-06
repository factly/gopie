import json
import logging
from collections.abc import AsyncGenerator

from app.models.router import Message
from app.workflow.graph import graph


async def stream_graph_updates(
    messages: list[Message],
    dataset_ids: list[str] | None = None,
    project_ids: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream graph updates for user input with event tracking.

    Args:
        user_input (str): The user's input query
        dataset_ids (List[str], optional): Specific dataset IDs to use for the
                                           query

    Yields:
        str: JSON-formatted event data for streaming
    """

    input_state = {
        # messages are converted to LangChain message format
        "messages": [message.model_dump() for message in messages],
        "dataset_ids": dataset_ids,
        "project_ids": project_ids,
    }

    try:
        async for event in graph.astream_events(input_state, version="v2"):
            if event.get("event", None) == "on_custom_event":
                formatted_event = json.dumps(event.get("data", {}), indent=2)
                logging.info(formatted_event)
                yield formatted_event + "\n\n"
    except Exception as e:
        error_event = json.dumps(
            {
                "type": "error",
                "message": f"Error during streaming: {e!s}",
                "data": {"error": str(e)},
            },
            indent=2,
        )
        yield error_event + "\n\n"
